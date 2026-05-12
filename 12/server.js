const express = require('express');
const http = require('http');
const path = require('path');
const { Server } = require('socket.io');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

app.use(express.static(path.join(__dirname, 'public')));

const rooms = new Map();
const userRooms = new Map();

function createRoom(roomId) {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, {
      id: roomId,
      users: new Map(),
      drawings: [],
      createdAt: Date.now()
    });
  }
  return rooms.get(roomId);
}

function getRoom(roomId) {
  return rooms.get(roomId);
}

function addUserToRoom(socket, roomId, username) {
  const room = createRoom(roomId);
  const user = {
    id: socket.id,
    username: username || `User_${socket.id.slice(0, 6)}`,
    color: getRandomColor(),
    joinedAt: Date.now()
  };
  
  room.users.set(socket.id, user);
  userRooms.set(socket.id, roomId);
  socket.join(roomId);
  
  return { user, room };
}

function removeUserFromRoom(socket) {
  try {
    const roomId = userRooms.get(socket.id);
    if (!roomId) return null;
    
    const room = rooms.get(roomId);
    if (!room) {
      userRooms.delete(socket.id);
      return null;
    }
    
    const user = room.users.get(socket.id);
    
    room.users.delete(socket.id);
    userRooms.delete(socket.id);
    
    try {
      socket.leave(roomId);
    } catch (err) {
      console.log(`Warning: failed to leave room ${roomId} for socket ${socket.id}`);
    }
    
    if (room.users.size === 0) {
      rooms.delete(roomId);
      console.log(`Room ${roomId} deleted (empty)`);
    }
    
    return { user, room, roomId };
  } catch (err) {
    console.error(`Error removing user from room:`, err);
    userRooms.delete(socket.id);
    return null;
  }
}

function addDrawing(roomId, drawing) {
  const room = getRoom(roomId);
  if (!room) return null;
  
  room.drawings.push(drawing);
  return drawing;
}

function clearRoomDrawings(roomId) {
  const room = getRoom(roomId);
  if (!room) return;
  
  room.drawings = [];
}

function getRoomUsers(roomId) {
  const room = getRoom(roomId);
  if (!room) return [];
  
  return Array.from(room.users.values());
}

function getRandomColor() {
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
    '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
  ];
  return colors[Math.floor(Math.random() * colors.length)];
}

io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);
  
  socket.on('join_room', (data) => {
    const { roomId, username } = data;
    const { user, room } = addUserToRoom(socket, roomId, username);
    
    socket.emit('user_joined', {
      user,
      users: getRoomUsers(roomId),
      drawings: room.drawings
    });
    
    socket.to(roomId).emit('user_joined_broadcast', {
      user,
      users: getRoomUsers(roomId)
    });
    
    console.log(`User ${user.username} joined room ${roomId}`);
  });
  
  socket.on('draw', (data) => {
    const roomId = userRooms.get(socket.id);
    if (!roomId) return;
    
    const drawing = {
      ...data,
      userId: socket.id,
      timestamp: Date.now()
    };
    
    addDrawing(roomId, drawing);
    socket.to(roomId).emit('draw', drawing);
  });
  
  socket.on('cursor_move', (data) => {
    const roomId = userRooms.get(socket.id);
    if (!roomId) return;
    
    socket.to(roomId).emit('cursor_move', {
      userId: socket.id,
      x: data.x,
      y: data.y,
      tool: data.tool
    });
  });

  socket.on('undo', (data) => {
    const roomId = userRooms.get(socket.id);
    if (!roomId) return;
    
    socket.to(roomId).emit('undo', {
      userId: socket.id,
      operationId: data.operationId
    });
    
    console.log(`User undo in room ${roomId}`);
  });

  socket.on('redo', (data) => {
    const roomId = userRooms.get(socket.id);
    if (!roomId) return;
    
    socket.to(roomId).emit('redo', {
      userId: socket.id,
      operationId: data.operationId
    });
    
    console.log(`User redo in room ${roomId}`);
  });
  
  socket.on('clear_canvas', () => {
    const roomId = userRooms.get(socket.id);
    if (!roomId) return;
    
    clearRoomDrawings(roomId);
    socket.to(roomId).emit('clear_canvas', {
      userId: socket.id
    });
  });
  
  socket.on('leave_room', () => {
    const result = removeUserFromRoom(socket);
    if (!result) return;
    
    const { user, roomId } = result;
    
    io.to(roomId).emit('user_left', {
      user,
      users: getRoomUsers(roomId)
    });
    
    console.log(`User ${user.username} left room ${roomId}`);
  });
  
  socket.on('disconnect', () => {
    const result = removeUserFromRoom(socket);
    
    if (result) {
      const { user, roomId } = result;
      
      io.to(roomId).emit('user_left', {
        user,
        users: getRoomUsers(roomId)
      });
      
      console.log(`User ${user.username} disconnected`);
    }
    
    console.log(`User disconnected: ${socket.id}`);
  });
});

const PORT = process.env.PORT || 3000;

server.listen(PORT, () => {
  console.log(`Whiteboard server running on http://localhost:${PORT}`);
  console.log(`Open multiple browser tabs with the same room ID to test collaboration`);
});
