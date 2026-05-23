const redis = require('./redis');
const { v4: uuidv4 } = require('uuid');

class ChatManager {
  constructor() {
    this.rooms = new Map();
    this.userSockets = new Map();
  }

  async createRoom(roomName, createdBy) {
    const roomId = uuidv4();
    const room = {
      id: roomId,
      name: roomName,
      createdBy,
      createdAt: Date.now(),
      users: [],
    };
    
    await redis.hset('rooms', roomId, JSON.stringify(room));
    return room;
  }

  async getRooms() {
    const roomsData = await redis.hgetall('rooms');
    return Object.values(roomsData).map(r => JSON.parse(r));
  }

  async getRoom(roomId) {
    const roomData = await redis.hget('rooms', roomId);
    return roomData ? JSON.parse(roomData) : null;
  }

  async addUserToRoom(roomId, user, ws) {
    const room = await this.getRoom(roomId);
    if (!room) return null;

    if (!room.users.find(u => u.id === user.id)) {
      room.users.push(user);
      await redis.hset('rooms', roomId, JSON.stringify(room));
    }

    if (!this.rooms.has(roomId)) {
      this.rooms.set(roomId, new Set());
    }
    this.rooms.get(roomId).add(ws);
    
    this.userSockets.set(user.id, { ws, roomId, user });

    return room;
  }

  async removeUserFromRoom(userId) {
    const userData = this.userSockets.get(userId);
    if (!userData) return;

    const { ws, roomId, user } = userData;
    const room = await this.getRoom(roomId);
    
    if (room) {
      room.users = room.users.filter(u => u.id !== userId);
      await redis.hset('rooms', roomId, JSON.stringify(room));
    }

    const roomSockets = this.rooms.get(roomId);
    if (roomSockets) {
      roomSockets.delete(ws);
      if (roomSockets.size === 0) {
        this.rooms.delete(roomId);
      }
    }

    this.userSockets.delete(userId);

    return { roomId, user };
  }

  getUserSocket(userId) {
    const data = this.userSockets.get(userId);
    return data ? data.ws : null;
  }

  getRoomSockets(roomId) {
    return this.rooms.get(roomId) || new Set();
  }

  async saveMessage(roomId, message) {
    const key = `messages:${roomId}`;
    await redis.lpush(key, JSON.stringify(message));
    await redis.ltrim(key, 0, 499);
  }

  async getMessages(roomId, count = 20) {
    const key = `messages:${roomId}`;
    const messages = await redis.lrange(key, 0, count - 1);
    return messages.map(m => JSON.parse(m)).reverse();
  }

  async getMessagesBefore(roomId, beforeTimestamp, count = 20) {
    const key = `messages:${roomId}`;
    const allMessages = await redis.lrange(key, 0, -1);
    const parsed = allMessages.map(m => JSON.parse(m));
    const older = parsed.filter(m => m.timestamp < beforeTimestamp);
    return older.slice(0, count).reverse();
  }

  async getTotalMessages(roomId) {
    const key = `messages:${roomId}`;
    return await redis.llen(key);
  }

  async incrementUnreadCount(roomId, userId) {
    const key = `unread:${userId}:${roomId}`;
    await redis.incr(key);
  }

  async getUnreadCount(roomId, userId) {
    const key = `unread:${userId}:${roomId}`;
    const count = await redis.get(key);
    return parseInt(count || 0);
  }

  async resetUnreadCount(roomId, userId) {
    const key = `unread:${userId}:${roomId}`;
    await redis.set(key, 0);
  }

  async getAllUnreadCounts(userId) {
    const rooms = await this.getRooms();
    const unreadCounts = {};
    for (const room of rooms) {
      unreadCounts[room.id] = await this.getUnreadCount(room.id, userId);
    }
    return unreadCounts;
  }

  async markMessageRead(roomId, userId, messageId) {
    const key = `read:${roomId}:${userId}`;
    const currentLast = await redis.get(key);
    if (!currentLast || messageId > currentLast) {
      await redis.set(key, messageId);
    }
    
    const room = await this.getRoom(roomId);
    if (room) {
      const readBy = await this.getMessageReadBy(roomId, messageId);
      return { messageId, readCount: readBy.length, readBy };
    }
    return null;
  }

  async getLastReadMessage(roomId, userId) {
    const key = `read:${roomId}:${userId}`;
    return await redis.get(key);
  }

  async getMessageReadBy(roomId, messageId) {
    const room = await this.getRoom(roomId);
    if (!room) return [];
    
    const readBy = [];
    for (const user of room.users) {
      const lastRead = await this.getLastReadMessage(roomId, user.id);
      if (lastRead && lastRead >= messageId) {
        readBy.push(user);
      }
    }
    return readBy;
  }

  async getMessagesWithReadStatus(roomId, userId, count = 20, before = null) {
    let messages;
    if (before) {
      messages = await this.getMessagesBefore(roomId, before, count);
    } else {
      messages = await this.getMessages(roomId, count);
    }
    
    const room = await this.getRoom(roomId);
    const totalUsers = room ? room.users.length : 0;
    
    const messagesWithStatus = await Promise.all(messages.map(async (msg) => {
      if (msg.userId === userId) {
        const readBy = await this.getMessageReadBy(roomId, msg.id);
        return { ...msg, readCount: readBy.length, readBy, totalUsers };
      }
      return { ...msg, totalUsers };
    }));
    
    return messagesWithStatus;
  }

  async searchMessages(roomId, { keyword, sender, startTime, endTime }) {
    const key = `messages:${roomId}`;
    const allMessages = await redis.lrange(key, 0, -1);
    let messages = allMessages.map(m => JSON.parse(m));
    
    if (keyword) {
      const lowerKeyword = keyword.toLowerCase();
      messages = messages.filter(m => 
        m.content.toLowerCase().includes(lowerKeyword)
      );
    }
    
    if (sender) {
      messages = messages.filter(m => 
        m.username.toLowerCase() === sender.toLowerCase()
      );
    }
    
    if (startTime) {
      messages = messages.filter(m => m.timestamp >= parseInt(startTime));
    }
    
    if (endTime) {
      messages = messages.filter(m => m.timestamp <= parseInt(endTime));
    }
    
    return messages.reverse();
  }
}

module.exports = new ChatManager();