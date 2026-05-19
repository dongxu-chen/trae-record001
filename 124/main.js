const { app, BrowserWindow, clipboard, ipcMain, dialog, nativeImage } = require('electron');
const path = require('path');
const fs = require('fs');
const os = require('os');
const crypto = require('crypto');
const zlib = require('zlib');
const bonjour = require('bonjour')();
const express = require('express');
const multer = require('multer');
const cors = require('cors');
const axios = require('axios');
const net = require('net');
const QRCode = require('qrcode');

let mainWindow;
let discoveredDevices = new Map();
let history = [];
let currentClipboardContent = null;
let httpServer = null;
const serverPort = 38765;
const HISTORY_FILE = path.join(app.getPath('userData'), 'clipboard-history.json');
const WHITELIST_FILE = path.join(app.getPath('userData'), 'device-whitelist.json');
const KEYS_FILE = path.join(app.getPath('userData'), 'ecc-keys.json');
const CHUNK_SIZE = 1024 * 1024;
const CONFIRM_TIMEOUT = 30000;
const MAX_RETRIES = 3;

const deviceName = `${os.hostname()}-${process.platform}`;
const deviceId = crypto.createHash('md5').update(deviceName + Date.now()).digest('hex').slice(0, 8);

let pendingRequests = new Map();
let fileTransfers = new Map();
let ipScanResults = new Map();
let whitelist = new Map();
let deviceKeys = null;
let sharedSecrets = new Map();
let pairingRequests = new Map();

function md5Hash(data) {
  return crypto.createHash('md5').update(data).digest('hex');
}

function generateECCKeys() {
  if (fs.existsSync(KEYS_FILE)) {
    try {
      const keysData = JSON.parse(fs.readFileSync(KEYS_FILE, 'utf8'));
      return {
        publicKey: Buffer.from(keysData.publicKey, 'base64'),
        privateKey: Buffer.from(keysData.privateKey, 'base64')
      };
    } catch (err) {
      console.error('加载密钥失败，重新生成:', err);
    }
  }
  
  const { publicKey, privateKey } = crypto.generateKeyPairSync('ec', {
    namedCurve: 'secp256r1',
    publicKeyEncoding: { type: 'spki', format: 'der' },
    privateKeyEncoding: { type: 'pkcs8', format: 'der' }
  });
  
  const keysData = {
    publicKey: publicKey.toString('base64'),
    privateKey: privateKey.toString('base64')
  };
  fs.writeFileSync(KEYS_FILE, JSON.stringify(keysData, null, 2));
  
  return { publicKey, privateKey };
}

function deriveSharedSecret(theirPublicKey) {
  const ecdh = crypto.createECDH('secp256r1');
  ecdh.setPrivateKey(deviceKeys.privateKey);
  const sharedSecret = ecdh.computeSecret(theirPublicKey);
  return crypto.createHash('sha256').update(sharedSecret).digest();
}

function encryptAESGCM(data, key) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return { iv, encrypted, authTag };
}

function decryptAESGCM(encrypted, iv, authTag, key) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);
  return Buffer.concat([decipher.update(encrypted), decipher.final()]);
}

function loadWhitelist() {
  try {
    if (fs.existsSync(WHITELIST_FILE)) {
      const data = JSON.parse(fs.readFileSync(WHITELIST_FILE, 'utf8'));
      data.forEach(device => whitelist.set(device.id, device));
    }
  } catch (err) {
    console.error('加载白名单失败:', err);
  }
}

function saveWhitelist() {
  try {
    const data = Array.from(whitelist.values());
    fs.writeFileSync(WHITELIST_FILE, JSON.stringify(data, null, 2));
  } catch (err) {
    console.error('保存白名单失败:', err);
  }
}

function isTrustedDevice(deviceId) {
  return whitelist.has(deviceId);
}

function addToWhitelist(device) {
  whitelist.set(device.id, {
    ...device,
    addedAt: new Date().toISOString()
  });
  saveWhitelist();
}

function removeFromWhitelist(deviceId) {
  whitelist.delete(deviceId);
  sharedSecrets.delete(deviceId);
  saveWhitelist();
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 850,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadFile('index.html');
  
  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function loadHistory() {
  try {
    if (fs.existsSync(HISTORY_FILE)) {
      const data = fs.readFileSync(HISTORY_FILE, 'utf8');
      history = JSON.parse(data);
    }
  } catch (err) {
    console.error('加载历史记录失败:', err);
    history = [];
  }
}

function saveHistory() {
  try {
    const dir = path.dirname(HISTORY_FILE);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(HISTORY_FILE, JSON.stringify(history.slice(0, 200), null, 2));
  } catch (err) {
    console.error('保存历史记录失败:', err);
  }
}

function addToHistory(item) {
  history.unshift({
    id: Date.now(),
    timestamp: new Date().toISOString(),
    encrypted: true,
    ...item
  });
  if (history.length > 200) history.pop();
  saveHistory();
}

function getLocalIPs() {
  const interfaces = os.networkInterfaces();
  const ips = [];
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === 'IPv4' && !iface.internal) {
        ips.push(iface.address);
      }
    }
  }
  return ips;
}

async function scanIPPort(ip, port, timeout = 2000) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(timeout);
    
    socket.on('connect', () => {
      socket.destroy();
      resolve({ ip, online: true });
    });
    
    socket.on('timeout', () => {
      socket.destroy();
      resolve({ ip, online: false });
    });
    
    socket.on('error', () => {
      resolve({ ip, online: false });
    });
    
    socket.connect(port, ip);
  });
}

async function scanIPRange(startIP, endIP) {
  const parts = startIP.split('.');
  const prefix = `${parts[0]}.${parts[1]}.${parts[2]}`;
  const start = parseInt(parts[3]);
  const end = parseInt(endIP.split('.')[3]);
  
  const promises = [];
  for (let i = start; i <= end; i++) {
    const ip = `${prefix}.${i}`;
    promises.push(scanIPPort(ip, serverPort));
  }
  
  const results = await Promise.all(promises);
  const onlineIPs = results.filter(r => r.online).map(r => r.ip);
  
  for (const ip of onlineIPs) {
    try {
      const response = await axios.get(`http://${ip}:${serverPort}/api/device-info`, { timeout: 3000 });
      const deviceInfo = response.data;
      const devId = deviceInfo.deviceId || `ip-scan-${ip}`;
      
      if (!discoveredDevices.has(devId) && devId !== deviceId) {
        discoveredDevices.set(devId, {
          id: devId,
          name: deviceInfo.name,
          platform: deviceInfo.platform,
          address: ip,
          port: serverPort,
          source: 'ip-scan',
          publicKey: deviceInfo.publicKey,
          trusted: whitelist.has(devId)
        });
        
        if (mainWindow) {
          mainWindow.webContents.send('devices-updated', Array.from(discoveredDevices.values()));
        }
      }
    } catch (err) {
    }
  }
  
  return onlineIPs;
}

function startMDNS() {
  bonjour.publish({
    name: deviceName,
    type: 'clipboard-sync',
    port: serverPort,
    txt: {
      hostname: os.hostname(),
      platform: process.platform,
      deviceId: deviceId,
      publicKey: deviceKeys.publicKey.toString('base64')
    }
  });

  const browser = bonjour.find({ type: 'clipboard-sync' });

  browser.on('up', service => {
    if (service.name !== deviceName) {
      const address = service.addresses && service.addresses.find(a => a.includes('.')) || 'localhost';
      const devId = service.txt.deviceId || service.name;
      discoveredDevices.set(devId, {
        id: devId,
        name: service.txt.hostname || service.name,
        platform: service.txt.platform,
        host: service.host,
        address: address,
        port: service.port,
        source: 'mdns',
        publicKey: service.txt.publicKey,
        trusted: whitelist.has(devId)
      });
      
      if (mainWindow) {
        mainWindow.webContents.send('devices-updated', Array.from(discoveredDevices.values()));
      }
    }
  });

  browser.on('down', service => {
    const devId = service.txt.deviceId || service.name;
    discoveredDevices.delete(devId);
    if (mainWindow) {
      mainWindow.webContents.send('devices-updated', Array.from(discoveredDevices.values()));
    }
  });
}

function splitIntoChunks(data) {
  const chunks = [];
  const totalSize = data.length;
  const totalChunks = Math.ceil(totalSize / CHUNK_SIZE);
  
  for (let i = 0; i < totalChunks; i++) {
    const start = i * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, totalSize);
    const chunkData = data.slice(start, end);
    const chunkMd5 = md5Hash(chunkData);
    
    chunks.push({
      index: i,
      total: totalChunks,
      data: chunkData,
      md5: chunkMd5,
      size: chunkData.length
    });
  }
  
  return chunks;
}

async function sendChunks(device, fileId, chunks, metadata, retries = 0) {
  const baseURL = `http://${device.address}:${device.port}`;
  const sharedKey = sharedSecrets.get(device.id);
  
  try {
    for (const chunk of chunks) {
      const compressed = zlib.gzipSync(chunk.data);
      let finalData = compressed;
      let encryptionInfo = null;
      
      if (sharedKey && whitelist.has(device.id)) {
        const encrypted = encryptAESGCM(compressed, sharedKey);
        finalData = Buffer.concat([encrypted.iv, encrypted.authTag, encrypted.encrypted]);
        encryptionInfo = {
          iv: encrypted.iv.toString('base64'),
          authTag: encrypted.authTag.toString('base64')
        };
      }
      
      await axios.post(`${baseURL}/api/chunk`, {
        fileId,
        index: chunk.index,
        total: chunk.total,
        data: finalData.toString('base64'),
        md5: chunk.md5,
        encrypted: !!sharedKey,
        encryptionInfo,
        metadata
      }, { timeout: 60000 });
      
      if (mainWindow) {
        mainWindow.webContents.send('transfer-progress', {
          fileId,
          current: chunk.index + 1,
          total: chunk.total,
          percentage: Math.round(((chunk.index + 1) / chunk.total) * 100)
        });
      }
    }
    
    await axios.post(`${baseURL}/api/chunk-complete`, { fileId }, { timeout: 10000 });
    return true;
  } catch (err) {
    if (retries < MAX_RETRIES) {
      console.log(`重传文件分片，尝试 ${retries + 1}/${MAX_RETRIES}`);
      return sendChunks(device, fileId, chunks, metadata, retries + 1);
    }
    throw err;
  }
}

function startHTTPServer() {
  const expApp = express();
  expApp.use(cors());
  expApp.use(express.json({ limit: '500mb' }));
  
  const storage = multer.memoryStorage();
  const upload = multer({ storage, limits: { fileSize: 500 * 1024 * 1024 } });

  expApp.get('/api/device-info', (req, res) => {
    res.json({
      name: deviceName,
      platform: process.platform,
      hostname: os.hostname(),
      deviceId: deviceId,
      publicKey: deviceKeys.publicKey.toString('base64')
    });
  });

  expApp.post('/api/pairing-request', (req, res) => {
    const { fromDeviceId, fromDeviceName, fromPublicKey, pairingCode } = req.body;
    const requestId = `pair-${Date.now()}`;
    
    pairingRequests.set(requestId, {
      fromDeviceId,
      fromDeviceName,
      fromPublicKey,
      pairingCode,
      timestamp: Date.now()
    });
    
    if (mainWindow) {
      mainWindow.webContents.send('pairing-request', {
        requestId,
        fromDeviceName,
        fromDeviceId
      });
    }
    
    res.json({ status: 'pending', requestId });
  });

  expApp.post('/api/pairing-response', (req, res) => {
    const { requestId, accepted, fromDeviceId, myPublicKey } = req.body;
    const request = pairingRequests.get(requestId);
    
    if (request && accepted) {
      const theirPublicKey = Buffer.from(request.fromPublicKey, 'base64');
      const sharedSecret = deriveSharedSecret(theirPublicKey);
      sharedSecrets.set(request.fromDeviceId, sharedSecret);
      
      pairingRequests.delete(requestId);
    }
    
    if (mainWindow) {
      mainWindow.webContents.send('pairing-response', { requestId, accepted });
    }
    
    res.json({ status: 'received' });
  });

  expApp.post('/api/clipboard-request', (req, res) => {
    const { from, type, preview, fileId, totalSize, fromDeviceId } = req.body;
    const requestId = `req-${Date.now()}`;
    
    if (fromDeviceId && !whitelist.has(fromDeviceId)) {
      return res.status(403).json({ 
        error: '设备未在白名单中，请先配对',
        needPairing: true 
      });
    }
    
    pendingRequests.set(requestId, {
      from,
      type,
      preview,
      fileId,
      totalSize,
      fromDeviceId,
      timestamp: Date.now()
    });
    
    setTimeout(() => {
      if (pendingRequests.has(requestId)) {
        pendingRequests.delete(requestId);
        if (mainWindow) {
          mainWindow.webContents.send('request-timeout', { from, type });
        }
      }
    }, CONFIRM_TIMEOUT);
    
    if (mainWindow) {
      mainWindow.webContents.send('clipboard-request', { 
        from, 
        type, 
        preview, 
        requestId,
        totalSize,
        encrypted: sharedSecrets.has(fromDeviceId)
      });
    }
    res.json({ status: 'sent', requestId });
  });

  expApp.post('/api/clipboard-response', (req, res) => {
    const { from, accepted, requestId } = req.body;
    
    if (pendingRequests.has(requestId)) {
      pendingRequests.delete(requestId);
    }
    
    if (mainWindow) {
      mainWindow.webContents.send('clipboard-response', { from, accepted, requestId });
    }
    res.json({ status: 'received' });
  });

  expApp.post('/api/chunk', (req, res) => {
    const { fileId, index, total, data, md5, encrypted, encryptionInfo, metadata } = req.body;
    
    if (!fileTransfers.has(fileId)) {
      fileTransfers.set(fileId, {
        chunks: new Map(),
        totalChunks: total,
        metadata,
        receivedCount: 0,
        encrypted
      });
    }
    
    const transfer = fileTransfers.get(fileId);
    let buffer = Buffer.from(data, 'base64');
    
    if (encrypted && encryptionInfo) {
      const sharedKey = sharedSecrets.get(metadata.fromDeviceId);
      if (sharedKey) {
        const iv = buffer.slice(0, 12);
        const authTag = buffer.slice(12, 28);
        const encryptedData = buffer.slice(28);
        
        try {
          buffer = decryptAESGCM(encryptedData, iv, authTag, sharedKey);
        } catch (err) {
          return res.status(400).json({ error: '解密失败', index });
        }
      }
    }
    
    buffer = zlib.gunzipSync(buffer);
    
    const receivedMd5 = md5Hash(buffer);
    if (receivedMd5 !== md5) {
      return res.status(400).json({ error: 'MD5校验失败', index });
    }
    
    transfer.chunks.set(index, buffer);
    transfer.receivedCount++;
    
    res.json({ status: 'received', index });
  });

  expApp.post('/api/chunk-complete', async (req, res) => {
    const { fileId } = req.body;
    const transfer = fileTransfers.get(fileId);
    
    if (!transfer) {
      return res.status(404).json({ error: '传输不存在' });
    }
    
    if (transfer.chunks.size !== transfer.totalChunks) {
      return res.status(400).json({ 
        error: '分片不完整',
        received: transfer.chunks.size,
        total: transfer.totalChunks
      });
    }
    
    const sortedChunks = Array.from(transfer.chunks.entries())
      .sort((a, b) => a[0] - b[0])
      .map(e => e[1]);
    
    const fullData = Buffer.concat(sortedChunks);
    const { type, from, content, filename, fromDeviceId } = transfer.metadata;
    
    try {
      if (type === 'text') {
        const text = fullData.toString('utf8');
        clipboard.writeText(text);
        addToHistory({ type, content: text, from, direction: 'receive', fromDeviceId });
      } else if (type === 'image') {
        const image = nativeImage.createFromBuffer(fullData);
        clipboard.writeImage(image);
        addToHistory({ type, preview: '图片数据', from, direction: 'receive', fromDeviceId });
      } else if (type === 'file') {
        const result = await dialog.showSaveDialog(mainWindow, {
          title: '保存文件',
          defaultPath: filename
        });
        
        if (!result.canceled && result.filePath) {
          fs.writeFileSync(result.filePath, fullData);
          addToHistory({ 
            type: 'file', 
            content: filename,
            from, 
            direction: 'receive',
            fromDeviceId
          });
        }
      }
      
      fileTransfers.delete(fileId);
      res.json({ status: 'success' });
    } catch (err) {
      fileTransfers.delete(fileId);
      res.status(500).json({ error: err.message });
    }
  });

  httpServer = expApp.listen(serverPort, () => {
    console.log(`HTTP服务运行在端口 ${serverPort}`);
    startMDNS();
  });
}

function checkClipboard() {
  let newContent = null;
  
  const text = clipboard.readText();
  if (text && text.length > 0) {
    newContent = { type: 'text', content: text };
  } else {
    const image = clipboard.readImage();
    if (!image.isEmpty()) {
      newContent = { type: 'image', content: image.toPNG() };
    }
  }

  if (newContent && JSON.stringify(newContent) !== JSON.stringify(currentClipboardContent)) {
    currentClipboardContent = newContent;
    if (mainWindow) {
      const preview = newContent.type === 'text' 
        ? (newContent.content.length > 50 ? newContent.content.substring(0, 50) + '...' : newContent.content)
        : '图片数据';
      mainWindow.webContents.send('clipboard-changed', { 
        type: newContent.type, 
        preview 
      });
    }
  }
}

ipcMain.on('get-devices', (event) => {
  event.reply('devices-updated', Array.from(discoveredDevices.values()));
});

ipcMain.on('get-history', (event) => {
  event.reply('history-updated', history);
});

ipcMain.on('get-local-ips', (event) => {
  event.reply('local-ips', getLocalIPs());
});

ipcMain.on('get-whitelist', (event) => {
  event.reply('whitelist-updated', Array.from(whitelist.values()));
});

ipcMain.on('get-device-info', (event) => {
  event.reply('device-info', {
    deviceId,
    deviceName,
    publicKey: deviceKeys.publicKey.toString('base64')
  });
});

ipcMain.on('start-ip-scan', async (event, { startIP, endIP }) => {
  try {
    const result = await scanIPRange(startIP, endIP);
    event.reply('scan-complete', { found: result.length, ips: result });
  } catch (err) {
    event.reply('scan-error', { message: err.message });
  }
});

ipcMain.on('add-to-whitelist', (event, device) => {
  addToWhitelist(device);
  
  if (device.publicKey) {
    const theirPublicKey = Buffer.from(device.publicKey, 'base64');
    const sharedSecret = deriveSharedSecret(theirPublicKey);
    sharedSecrets.set(device.id, sharedSecret);
  }
  
  event.reply('whitelist-updated', Array.from(whitelist.values()));
});

ipcMain.on('remove-from-whitelist', (event, deviceId) => {
  removeFromWhitelist(deviceId);
  event.reply('whitelist-updated', Array.from(whitelist.values()));
});

ipcMain.on('respond-pairing', async (event, { requestId, accepted }) => {
  const request = pairingRequests.get(requestId);
  if (!request) return;
  
  if (accepted) {
    const theirPublicKey = Buffer.from(request.fromPublicKey, 'base64');
    const sharedSecret = deriveSharedSecret(theirPublicKey);
    sharedSecrets.set(request.fromDeviceId, sharedSecret);
    
    addToWhitelist({
      id: request.fromDeviceId,
      name: request.fromDeviceName,
      publicKey: request.fromPublicKey
    });
  }
  
  pairingRequests.delete(requestId);
  event.reply('pairing-completed', { accepted });
});

ipcMain.on('send-pairing-request', async (event, deviceId) => {
  const device = discoveredDevices.get(deviceId);
  if (!device) {
    event.reply('pairing-error', '设备不存在');
    return;
  }
  
  const pairingCode = Math.random().toString(36).substring(2, 8).toUpperCase();
  
  try {
    await axios.post(`http://${device.address}:${device.port}/api/pairing-request`, {
      fromDeviceId: deviceId,
      fromDeviceName: deviceName,
      fromPublicKey: deviceKeys.publicKey.toString('base64'),
      pairingCode
    }, { timeout: 10000 });
    
    event.reply('pairing-sent', { deviceName: device.name, pairingCode });
  } catch (err) {
    event.reply('pairing-error', err.message);
  }
});

ipcMain.on('generate-qrcode', async (event) => {
  const localIPs = getLocalIPs();
  const pairingData = {
    deviceId,
    deviceName,
    publicKey: deviceKeys.publicKey.toString('base64'),
    ips: localIPs,
    port: serverPort,
    timestamp: Date.now()
  };
  
  const qrData = JSON.stringify(pairingData);
  const qrImage = await QRCode.toDataURL(qrData, {
    width: 300,
    margin: 2,
    color: {
      dark: '#000000',
      light: '#ffffff'
    }
  });
  
  event.reply('qrcode-generated', qrImage);
});

ipcMain.on('scan-qrcode', (event, qrData) => {
  try {
    const data = JSON.parse(qrData);
    
    if (!data.deviceId || !data.publicKey) {
      event.reply('qrscan-error', '无效的二维码数据');
      return;
    }
    
    discoveredDevices.set(data.deviceId, {
      id: data.deviceId,
      name: data.deviceName,
      platform: 'unknown',
      address: data.ips[0] || '',
      port: data.port,
      source: 'qrcode',
      publicKey: data.publicKey,
      trusted: false
    });
    
    event.reply('qrscan-success', {
      deviceId: data.deviceId,
      deviceName: data.deviceName
    });
    
    if (mainWindow) {
      mainWindow.webContents.send('devices-updated', Array.from(discoveredDevices.values()));
    }
  } catch (err) {
    event.reply('qrscan-error', err.message);
  }
});

ipcMain.on('send-clipboard', async (event, deviceId) => {
  const device = discoveredDevices.get(deviceId);
  if (!device || !currentClipboardContent) {
    event.reply('send-error', '设备不存在或剪贴板为空');
    return;
  }
  
  if (!whitelist.has(deviceId)) {
    event.reply('send-error', '设备未在白名单中，请先配对');
    return;
  }

  try {
    const fileId = `transfer-${Date.now()}`;
    let data, preview, totalSize;
    
    if (currentClipboardContent.type === 'text') {
      data = Buffer.from(currentClipboardContent.content, 'utf8');
      preview = currentClipboardContent.content.substring(0, 50) + '...';
      totalSize = data.length;
    } else {
      data = currentClipboardContent.content;
      preview = '图片数据';
      totalSize = data.length;
    }
    
    await axios.post(`http://${device.address}:${device.port}/api/clipboard-request`, {
      from: deviceName,
      type: currentClipboardContent.type,
      preview,
      fileId,
      totalSize,
      fromDeviceId: deviceId
    }, { timeout: CONFIRM_TIMEOUT });

    mainWindow.webContents.send('send-status', { 
      status: 'waiting', 
      device: device.name,
      fileId,
      type: currentClipboardContent.type
    });
    
    pendingRequests.set(fileId, {
      device,
      data,
      type: currentClipboardContent.type,
      preview,
      timestamp: Date.now(),
      retries: 0,
      fromDeviceId: deviceId
    });
    
  } catch (err) {
    if (err.response && err.response.data.needPairing) {
      event.reply('send-error', '设备需要配对，请先添加到白名单');
    } else {
      event.reply('send-error', '发送请求失败: ' + err.message);
    }
  }
});

ipcMain.on('send-file', async (event, { deviceId, filePath }) => {
  const device = discoveredDevices.get(deviceId);
  if (!device) {
    event.reply('send-error', '设备不存在');
    return;
  }
  
  if (!whitelist.has(deviceId)) {
    event.reply('send-error', '设备未在白名单中，请先配对');
    return;
  }

  try {
    const fileId = `transfer-${Date.now()}`;
    const filename = path.basename(filePath);
    const stats = fs.statSync(filePath);
    
    await axios.post(`http://${device.address}:${device.port}/api/clipboard-request`, {
      from: deviceName,
      type: 'file',
      preview: filename,
      fileId,
      totalSize: stats.size,
      fromDeviceId: deviceId
    }, { timeout: CONFIRM_TIMEOUT });

    mainWindow.webContents.send('send-status', { 
      status: 'waiting', 
      device: device.name,
      filePath,
      deviceId,
      fileId,
      type: 'file'
    });
    
    pendingRequests.set(fileId, {
      device,
      filePath,
      type: 'file',
      preview: filename,
      timestamp: Date.now(),
      retries: 0,
      fromDeviceId: deviceId
    });
    
  } catch (err) {
    if (err.response && err.response.data.needPairing) {
      event.reply('send-error', '设备需要配对，请先添加到白名单');
    } else {
      event.reply('send-error', '发送请求失败: ' + err.message);
    }
  }
});

ipcMain.on('respond-clipboard', async (event, { from, accepted, requestId }) => {
  const device = Array.from(discoveredDevices.values()).find(d => d.name === from || d.id === from);
  
  if (device) {
    try {
      await axios.post(`http://${device.address}:${device.port}/api/clipboard-response`, {
        from: deviceName,
        accepted,
        requestId
      });
    } catch (err) {
    }
  }
  
  event.reply('respond-sent');
});

ipcMain.on('confirm-file-send', async (event, { fileId, accepted }) => {
  const request = pendingRequests.get(fileId);
  if (!request) return;
  
  pendingRequests.delete(fileId);
  
  if (!accepted) return;
  
  try {
    const { device, type } = request;
    let data, filename, content;
    
    if (type === 'file') {
      data = fs.readFileSync(request.filePath);
      filename = path.basename(request.filePath);
      content = filename;
    } else if (type === 'text') {
      data = request.data;
      content = request.data.toString('utf8');
    } else {
      data = request.data;
      content = '图片数据';
    }
    
    const chunks = splitIntoChunks(data);
    
    await sendChunks(device, fileId, chunks, {
      type,
      from: deviceName,
      filename,
      content,
      fromDeviceId: deviceId
    });
    
    addToHistory({
      type,
      content,
      to: device.name,
      direction: 'send',
      toDeviceId: device.id
    });
    
  } catch (err) {
    if (mainWindow) {
      mainWindow.webContents.send('send-error', '传输失败: ' + err.message);
    }
  }
});

ipcMain.on('select-file', (event) => {
  dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    title: '选择要发送的文件'
  }).then(result => {
    if (!result.canceled && result.filePaths.length > 0) {
      event.reply('file-selected', result.filePaths[0]);
    }
  });
});

ipcMain.on('clear-history', (event) => {
  history = [];
  saveHistory();
  event.reply('history-updated', history);
});

ipcMain.on('search-history', (event, { keyword, type, startDate, endDate }) => {
  let filtered = [...history];
  
  if (keyword && keyword.trim()) {
    const kw = keyword.toLowerCase();
    filtered = filtered.filter(h => 
      h.content && h.content.toLowerCase().includes(kw) ||
      h.from && h.from.toLowerCase().includes(kw) ||
      h.to && h.to.toLowerCase().includes(kw)
    );
  }
  
  if (type && type !== 'all') {
    filtered = filtered.filter(h => h.type === type);
  }
  
  if (startDate) {
    const start = new Date(startDate);
    filtered = filtered.filter(h => new Date(h.timestamp) >= start);
  }
  
  if (endDate) {
    const end = new Date(endDate);
    end.setHours(23, 59, 59);
    filtered = filtered.filter(h => new Date(h.timestamp) <= end);
  }
  
  event.reply('search-results', filtered);
});

app.whenReady().then(() => {
  deviceKeys = generateECCKeys();
  loadWhitelist();
  loadHistory();
  startHTTPServer();
  createWindow();
  
  setInterval(checkClipboard, 1000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('quit', () => {
  if (httpServer) httpServer.close();
  bonjour.destroy();
});
