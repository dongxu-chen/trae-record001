const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { v4: uuidv4 } = require('uuid');
const chatManager = require('./ChatManager');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

const uploadDir = path.join(__dirname, 'uploads', 'voices');
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir, { recursive: true });
}

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    cb(null, `${Date.now()}_${uuidv4()}${ext}`);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    if (file.mimetype.startsWith('audio/')) {
      cb(null, true);
    } else {
      cb(new Error('只允许上传音频文件'));
    }
  }
});

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.get('/api/rooms', async (req, res) => {
  try {
    const rooms = await chatManager.getRooms();
    res.json(rooms);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/rooms', async (req, res) => {
  try {
    const { name, createdBy } = req.body;
    if (!name || !createdBy) {
      return res.status(400).json({ error: 'Name and createdBy are required' });
    }
    const room = await chatManager.createRoom(name, createdBy);
    res.json(room);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/rooms/:roomId/messages', async (req, res) => {
  try {
    const { before, count = 20, userId } = req.query;
    let messages;
    if (userId) {
      messages = await chatManager.getMessagesWithReadStatus(
        req.params.roomId, 
        userId, 
        parseInt(count), 
        before ? parseInt(before) : null
      );
    } else {
      if (before) {
        messages = await chatManager.getMessagesBefore(req.params.roomId, parseInt(before), parseInt(count));
      } else {
        messages = await chatManager.getMessages(req.params.roomId, parseInt(count));
      }
    }
    res.json(messages);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/rooms/:roomId/search', async (req, res) => {
  try {
    const { keyword, sender, startTime, endTime } = req.query;
    const results = await chatManager.searchMessages(req.params.roomId, {
      keyword, sender, startTime, endTime
    });
    res.json(results);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/upload/voice', upload.single('voice'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: '没有上传文件' });
    }
    const baseUrl = `${req.protocol}://${req.get('host')}`;
    const fileUrl = `${baseUrl}/uploads/voices/${req.file.filename}`;
    res.json({
      url: fileUrl,
      filename: req.file.filename,
      size: req.file.size,
      duration: req.body.duration || 0
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/users/:userId/unread', async (req, res) => {
  try {
    const counts = await chatManager.getAllUnreadCounts(req.params.userId);
    res.json(counts);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

const typingUsers = new Map();
const HEARTBEAT_INTERVAL = 30000;

wss.on('connection', (ws) => {
  let currentUser = null;
  let currentRoomId = null;
  let isAlive = true;

  const heartbeat = setInterval(() => {
    if (!isAlive) {
      ws.terminate();
      return;
    }
    isAlive = false;
    ws.ping();
  }, HEARTBEAT_INTERVAL);

  ws.on('pong', () => {
    isAlive = true;
  });

  ws.on('message', async (data) => {
    try {
      const message = JSON.parse(data.toString());
      
      switch (message.type) {
        case 'pong': {
          isAlive = true;
          break;
        }
        case 'join': {
          const { user, roomId } = message.payload;
          currentUser = user;
          currentRoomId = roomId;
          
          await chatManager.addUserToRoom(roomId, user, ws);
          await chatManager.resetUnreadCount(roomId, user.id);
          
          const room = await chatManager.getRoom(roomId);
          const messages = await chatManager.getMessagesWithReadStatus(roomId, user.id, 20);
          
          broadcastToRoom(roomId, {
            type: 'user_joined',
            payload: { user, room }
          });
          
          ws.send(JSON.stringify({
            type: 'joined',
            payload: { room, messages }
          }));
          break;
        }

        case 'message':
        case 'voice': {
          const { roomId, content, mentions, type: msgType, duration, url } = message.payload;
          const msg = {
            id: uuidv4(),
            userId: currentUser.id,
            username: currentUser.username,
            content,
            type: msgType || 'text',
            mentions: mentions || [],
            timestamp: Date.now(),
            ...(msgType === 'voice' && { duration, url })
          };
          
          await chatManager.saveMessage(roomId, msg);
          
          const room = await chatManager.getRoom(roomId);
          if (room) {
            for (const user of room.users) {
              if (user.id !== currentUser.id) {
                await chatManager.incrementUnreadCount(roomId, user.id);
              }
            }
          }
          
          const msgWithStatus = await chatManager.getMessagesWithReadStatus(roomId, currentUser.id, 1);
          const latestMsg = msgWithStatus[msgWithStatus.length - 1] || msg;
          
          broadcastToRoom(roomId, {
            type: 'message',
            payload: latestMsg
          });
          break;
        }

        case 'typing': {
          const { roomId, isTyping } = message.payload;
          const key = `${roomId}:${currentUser.id}`;
          
          if (isTyping) {
            typingUsers.set(key, { user: currentUser, roomId, timestamp: Date.now() });
          } else {
            typingUsers.delete(key);
          }
          
          const typingInRoom = Array.from(typingUsers.values())
            .filter(t => t.roomId === roomId && t.user.id !== currentUser.id)
            .map(t => t.user);
          
          broadcastToRoom(roomId, {
            type: 'typing',
            payload: { users: typingInRoom }
          });
          break;
        }

        case 'mark_read': {
          const { roomId, userId } = message.payload;
          await chatManager.resetUnreadCount(roomId, userId);
          break;
        }

        case 'read_receipt': {
          const { roomId, messageId } = message.payload;
          const result = await chatManager.markMessageRead(roomId, currentUser.id, messageId);
          if (result) {
            broadcastToRoom(roomId, {
              type: 'read_status',
              payload: {
                messageId: result.messageId,
                readCount: result.readCount,
                readBy: result.readBy,
                userId: currentUser.id
              }
            });
          }
          break;
        }
      }
    } catch (error) {
      console.error('Error handling message:', error);
    }
  });

  ws.on('close', async () => {
    clearInterval(heartbeat);
    
    if (currentUser && currentRoomId) {
      const result = await chatManager.removeUserFromRoom(currentUser.id);
      if (result) {
        broadcastToRoom(result.roomId, {
          type: 'user_left',
          payload: { user: result.user }
        });
      }
      
      const keyPrefix = `${currentRoomId}:${currentUser.id}`;
      for (const [key] of typingUsers) {
        if (key.startsWith(keyPrefix)) {
          typingUsers.delete(key);
        }
      }
      
      const typingInRoom = Array.from(typingUsers.values())
        .filter(t => t.roomId === currentRoomId)
        .map(t => t.user);
      
      broadcastToRoom(currentRoomId, {
        type: 'typing',
        payload: { users: typingInRoom }
      });
    }
  });
});

function broadcastToRoom(roomId, data) {
  const sockets = chatManager.getRoomSockets(roomId);
  const message = JSON.stringify(data);
  
  for (const ws of sockets) {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(message);
    }
  }
}

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});