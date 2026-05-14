const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const storage = require('./storage.js');

const app = express();
app.use(cors());
app.use(express.json({ limit: '10mb' }));

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  },
  pingInterval: 25000,
  pingTimeout: 60000,
  maxHttpBufferSize: 10 * 1024 * 1024
});

const rooms = new Map();
const socketToRoom = new Map();
const typingUsers = new Map();
const TYPING_TIMEOUT = 5000;

app.get('/api/history/:roomId', async (req, res) => {
  try {
    const { roomId } = req.params;
    const messages = await storage.getRoomMessages(roomId, 100);
    res.json({ success: true, messages });
  } catch (error) {
    console.error('Error fetching history:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch history' });
  }
});

app.post('/api/history/:roomId', async (req, res) => {
  try {
    const { roomId } = req.params;
    const message = req.body;
    
    if (!message || !message.encrypted) {
      return res.status(400).json({ success: false, error: 'Invalid message' });
    }
    
    const saved = await storage.saveMessage(roomId, message);
    res.json({ success: true, message: saved });
  } catch (error) {
    console.error('Error saving message:', error);
    res.status(500).json({ success: false, error: 'Failed to save message' });
  }
});

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);
  let typingTimer = null;

  socket.on('join-room', async (roomId) => {
    console.log('User', socket.id, 'joining room', roomId);
    
    if (!rooms.has(roomId)) {
      rooms.set(roomId, new Set());
    }
    
    const room = rooms.get(roomId);
    const previousRoom = socketToRoom.get(socket.id);
    
    if (previousRoom && previousRoom !== roomId) {
      const prevRoom = rooms.get(previousRoom);
      if (prevRoom) {
        prevRoom.delete(socket.id);
        io.to(previousRoom).emit('user-left', socket.id);
        io.to(previousRoom).emit('typing', { userId: socket.id, isTyping: false });
        console.log('User', socket.id, 'left previous room', previousRoom);
        
        if (prevRoom.size === 0) {
          rooms.delete(previousRoom);
        }
      }
    }
    
    room.add(socket.id);
    socketToRoom.set(socket.id, roomId);
    socket.join(roomId);

    const usersInRoom = Array.from(room);
    socket.emit('room-users', usersInRoom);
    
    io.to(roomId).emit('user-joined', socket.id);
    console.log('User', socket.id, 'joined room', roomId, '| users:', usersInRoom.length);
  });

  socket.on('leave-room', () => {
    const roomId = socketToRoom.get(socket.id);
    if (!roomId) return;
    
    const room = rooms.get(roomId);
    if (room) {
      room.delete(socket.id);
      socket.leave(roomId);
      socketToRoom.delete(socket.id);
      
      io.to(roomId).emit('user-left', socket.id);
      io.to(roomId).emit('typing', { userId: socket.id, isTyping: false });
      console.log('User', socket.id, 'left room', roomId);
      
      if (room.size === 0) {
        rooms.delete(roomId);
        console.log('Room', roomId, 'closed (empty)');
      }
    }
  });

  socket.on('typing', (data) => {
    const { isTyping } = data;
    const roomId = socketToRoom.get(socket.id);
    
    if (!roomId) return;
    
    if (typingTimer) {
      clearTimeout(typingTimer);
      typingTimer = null;
    }
    
    io.to(roomId).emit('typing', { 
      userId: socket.id, 
      isTyping 
    });
    
    if (isTyping) {
      typingTimer = setTimeout(() => {
        io.to(roomId).emit('typing', { 
          userId: socket.id, 
          isTyping: false 
        });
      }, TYPING_TIMEOUT);
    }
  });

  socket.on('offer', (data) => {
    const { to, offer } = data;
    if (!to || !offer) {
      console.warn('Invalid offer received from', socket.id);
      return;
    }
    socket.to(to).emit('offer', {
      from: socket.id,
      offer
    });
  });

  socket.on('answer', (data) => {
    const { to, answer } = data;
    if (!to || !answer) {
      console.warn('Invalid answer received from', socket.id);
      return;
    }
    socket.to(to).emit('answer', {
      from: socket.id,
      answer
    });
  });

  socket.on('ice-candidate', (data) => {
    const { to, candidate } = data;
    if (!to || !candidate) {
      return;
    }
    socket.to(to).emit('ice-candidate', {
      from: socket.id,
      candidate
    });
  });

  socket.on('key-verify', (data) => {
    const { to } = data;
    if (!to) return;
    socket.to(to).emit('key-verify', {
      from: socket.id,
      ...data
    });
  });

  socket.on('key-confirm', (data) => {
    const { to } = data;
    if (!to) return;
    socket.to(to).emit('key-confirm', {
      from: socket.id,
      ...data
    });
  });

  socket.on('offline-message', async (data) => {
    const roomId = socketToRoom.get(socket.id);
    if (!roomId) return;
    
    const { targetUserId, encryptedMessage } = data;
    if (!targetUserId || !encryptedMessage) return;
    
    try {
      await storage.saveOfflineMessage(roomId, {
        targetUserId,
        fromUserId: socket.id,
        encryptedMessage,
        timestamp: Date.now()
      });
      console.log('Offline message saved for user', targetUserId);
    } catch (error) {
      console.error('Error saving offline message:', error);
    }
  });

  socket.on('request-offline-messages', async () => {
    const roomId = socketToRoom.get(socket.id);
    if (!roomId) return;
    
    try {
      const messages = await storage.getOfflineMessages(roomId, socket.id);
      if (messages.length > 0) {
        socket.emit('offline-messages', { messages });
        await storage.clearOfflineMessages(roomId, socket.id);
        console.log('Delivered', messages.length, 'offline messages to', socket.id);
      }
    } catch (error) {
      console.error('Error fetching offline messages:', error);
    }
  });

  socket.on('disconnect', () => {
    console.log('User disconnected:', socket.id);
    
    if (typingTimer) {
      clearTimeout(typingTimer);
    }
    
    const roomId = socketToRoom.get(socket.id);
    if (roomId) {
      const room = rooms.get(roomId);
      if (room) {
        room.delete(socket.id);
        socketToRoom.delete(socket.id);
        
        io.to(roomId).emit('user-left', socket.id);
        io.to(roomId).emit('typing', { userId: socket.id, isTyping: false });
        console.log('User', socket.id, 'removed from room', roomId, 'on disconnect');
        
        if (room.size === 0) {
          rooms.delete(roomId);
          console.log('Room', roomId, 'closed (empty after disconnect)');
        }
      }
    }
  });
});

const PORT = process.env.PORT || 3001;
storage.initialize().then(() => {
  server.listen(PORT, () => {
    console.log('Signaling server running on port', PORT);
    console.log('Server started at', new Date().toISOString());
  });
}).catch(error => {
  console.error('Failed to initialize storage:', error);
  process.exit(1);
});
