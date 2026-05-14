const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const DATA_DIR = path.join(__dirname, 'data');
const HISTORY_DIR = path.join(DATA_DIR, 'history');
const OFFLINE_DIR = path.join(DATA_DIR, 'offline');
const MAX_HISTORY_PER_ROOM = 500;
const MAX_OFFLINE_PER_USER = 100;
const OFFLINE_EXPIRE_DAYS = 7;

const ensureDir = (dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
};

const getRoomFilePath = (roomId) => {
  const safeRoomId = crypto.createHash('sha256').update(roomId).digest('hex');
  return path.join(HISTORY_DIR, `${safeRoomId}.json`);
};

const getOfflineFilePath = (roomId) => {
  const safeRoomId = crypto.createHash('sha256').update(roomId).digest('hex');
  return path.join(OFFLINE_DIR, `${safeRoomId}.json`);
};

const readJsonFile = (filePath) => {
  try {
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(content);
    }
  } catch (error) {
    console.error('Error reading file:', error);
  }
  return [];
};

const writeJsonFile = (filePath, data) => {
  try {
    const tempPath = filePath + '.tmp';
    fs.writeFileSync(tempPath, JSON.stringify(data, null, 2));
    fs.renameSync(tempPath, filePath);
    return true;
  } catch (error) {
    console.error('Error writing file:', error);
    return false;
  }
};

const storage = {
  async initialize() {
    ensureDir(DATA_DIR);
    ensureDir(HISTORY_DIR);
    ensureDir(OFFLINE_DIR);
    console.log('Storage initialized');
  },

  async saveMessage(roomId, message) {
    const filePath = getRoomFilePath(roomId);
    const messages = readJsonFile(filePath);
    
    const newMessage = {
      ...message,
      id: crypto.randomUUID(),
      storedAt: Date.now()
    };
    
    messages.push(newMessage);
    
    if (messages.length > MAX_HISTORY_PER_ROOM) {
      messages.splice(0, messages.length - MAX_HISTORY_PER_ROOM);
    }
    
    writeJsonFile(filePath, messages);
    return newMessage;
  },

  async getRoomMessages(roomId, limit = 100) {
    const filePath = getRoomFilePath(roomId);
    const messages = readJsonFile(filePath);
    
    const sorted = messages.sort((a, b) => a.storedAt - b.storedAt);
    return sorted.slice(-limit);
  },

  async clearRoomHistory(roomId) {
    const filePath = getRoomFilePath(roomId);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
    }
    return true;
  },

  async saveOfflineMessage(roomId, message) {
    const filePath = getOfflineFilePath(roomId);
    const allOffline = readJsonFile(filePath);
    
    const { targetUserId } = message;
    if (!allOffline[targetUserId]) {
      allOffline[targetUserId] = [];
    }
    
    allOffline[targetUserId].push({
      ...message,
      id: crypto.randomUUID(),
      storedAt: Date.now()
    });
    
    if (allOffline[targetUserId].length > MAX_OFFLINE_PER_USER) {
      allOffline[targetUserId].splice(0, allOffline[targetUserId].length - MAX_OFFLINE_PER_USER);
    }
    
    writeJsonFile(filePath, allOffline);
    return true;
  },

  async getOfflineMessages(roomId, userId) {
    const filePath = getOfflineFilePath(roomId);
    const allOffline = readJsonFile(filePath);
    
    const messages = allOffline[userId] || [];
    const cutoffTime = Date.now() - (OFFLINE_EXPIRE_DAYS * 24 * 60 * 60 * 1000);
    
    return messages.filter(msg => msg.storedAt >= cutoffTime);
  },

  async clearOfflineMessages(roomId, userId) {
    const filePath = getOfflineFilePath(roomId);
    const allOffline = readJsonFile(filePath);
    
    if (allOffline[userId]) {
      delete allOffline[userId];
      
      if (Object.keys(allOffline).length === 0) {
        if (fs.existsSync(filePath)) {
          fs.unlinkSync(filePath);
        }
      } else {
        writeJsonFile(filePath, allOffline);
      }
    }
    return true;
  },

  async cleanupExpiredOffline() {
    const cutoffTime = Date.now() - (OFFLINE_EXPIRE_DAYS * 24 * 60 * 60 * 1000);
    
    if (!fs.existsSync(OFFLINE_DIR)) return;
    
    const files = fs.readdirSync(OFFLINE_DIR);
    for (const file of files) {
      if (!file.endsWith('.json')) continue;
      
      const filePath = path.join(OFFLINE_DIR, file);
      const allOffline = readJsonFile(filePath);
      let hasChanges = false;
      
      for (const [userId, messages] of Object.entries(allOffline)) {
        const beforeCount = messages.length;
        allOffline[userId] = messages.filter(msg => msg.storedAt >= cutoffTime);
        if (allOffline[userId].length < beforeCount) {
          hasChanges = true;
        }
        if (allOffline[userId].length === 0) {
          delete allOffline[userId];
        }
      }
      
      if (hasChanges) {
        if (Object.keys(allOffline).length === 0) {
          fs.unlinkSync(filePath);
        } else {
          writeJsonFile(filePath, allOffline);
        }
      }
    }
  }
};

setInterval(() => {
  storage.cleanupExpiredOffline().catch(console.error);
}, 60 * 60 * 1000);

module.exports = storage;
