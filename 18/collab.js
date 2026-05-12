const rooms = new Map();
const roomMetadata = new Map();

function getOrCreateRoom(roomId, wsServer) {
  if (rooms.has(roomId)) {
    return rooms.get(roomId);
  }

  const room = {
    id: roomId,
    users: new Map(),
    createdAt: Date.now(),
    lastActivity: Date.now()
  };

  rooms.set(roomId, room);
  roomMetadata.set(roomId, {
    code: '',
    language: 'javascript',
    output: []
  });

  console.log(`[协同] 房间 ${roomId} 已创建`);
  return room;
}

function removeUserFromRoom(roomId, clientId, userId) {
  const room = rooms.get(roomId);
  if (!room) return;

  room.users.delete(clientId);
  room.lastActivity = Date.now();

  console.log(`[协同] 用户 ${userId} 离开房间 ${roomId}`);

  if (room.users.size === 0) {
    setTimeout(() => {
      const currentRoom = rooms.get(roomId);
      if (currentRoom && currentRoom.users.size === 0) {
        rooms.delete(roomId);
        roomMetadata.delete(roomId);
        console.log(`[协同] 房间 ${roomId} 已销毁（无用户）`);
      }
    }, 60000);
  }
}

function broadcastToRoom(roomId, event, data, excludeClientId = null) {
  const room = rooms.get(roomId);
  if (!room) return;

  room.users.forEach((user, clientId) => {
    if (clientId !== excludeClientId && user.ws && user.ws.readyState === 1) {
      user.ws.send(JSON.stringify({ event, data }));
    }
  });
}

function getUserInfo(ws, userId, userName) {
  return {
    ws,
    userId,
    userName,
    joinedAt: Date.now(),
    cursor: null,
    selection: null
  };
}

function handleCollabConnection(ws, req, next) {
  const url = new URL(req.url, 'http://localhost');
  const roomId = url.pathname.split('/').pop().replace(/^room-/, '');
  const userId = url.searchParams.get('userId') || `user-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const userName = url.searchParams.get('userName') || `用户${userId.slice(-4)}`;

  if (!roomId || roomId === 'collab') {
    if (next) return next();
    ws.close(4000, '无效的房间ID');
    return;
  }

  const room = getOrCreateRoom(roomId);
  const userInfo = getUserInfo(ws, userId, userName);
  const clientId = `${userId}-${Date.now()}`;

  room.users.set(clientId, userInfo);
  room.lastActivity = Date.now();

  console.log(`[协同] 用户 ${userName} (${userId}) 加入房间 ${roomId}, 当前 ${room.users.size} 人`);

  broadcastToRoom(roomId, 'userJoined', {
    userId,
    userName,
    joinedAt: Date.now()
  }, clientId);

  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message.toString());
      room.lastActivity = Date.now();

      switch (data.event) {
        case 'cursor':
          if (data.position) {
            userInfo.cursor = data.position;
            broadcastToRoom(roomId, 'cursorUpdate', {
              userId,
              userName,
              position: data.position
            }, clientId);
          }
          break;

        case 'selection':
          userInfo.selection = data.selection;
          broadcastToRoom(roomId, 'selectionUpdate', {
            userId,
            userName,
            selection: data.selection
          }, clientId);
          break;

        case 'chat':
          broadcastToRoom(roomId, 'chatMessage', {
            userId,
            userName,
            message: data.message,
            timestamp: Date.now()
          });
          break;

        case 'languageChange':
          if (roomMetadata.has(roomId)) {
            roomMetadata.get(roomId).language = data.language;
            broadcastToRoom(roomId, 'languageChanged', {
              userId,
              userName,
              language: data.language,
              timestamp: Date.now()
            });
          }
          break;

        case 'runCode':
          broadcastToRoom(roomId, 'codeRunning', {
            userId,
            userName,
            timestamp: Date.now()
          });
          break;

        case 'output':
          if (roomMetadata.has(roomId)) {
            const metadata = roomMetadata.get(roomId);
            metadata.output.push(data.output);
            if (metadata.output.length > 100) {
              metadata.output = metadata.output.slice(-100);
            }
          }
          break;

        case 'clearOutput':
          if (roomMetadata.has(roomId)) {
            roomMetadata.get(roomId).output = [];
          }
          broadcastToRoom(roomId, 'outputCleared', {
            userId,
            userName,
            timestamp: Date.now()
          });
          break;

        default:
          break;
      }
    } catch (error) {
      console.error('[协同] 消息解析错误:', error.message);
    }
  });

  ws.on('close', () => {
    removeUserFromRoom(roomId, clientId, userId);
    broadcastToRoom(roomId, 'userLeft', {
      userId,
      userName,
      leftAt: Date.now()
    });
  });

  ws.on('error', (error) => {
    console.error('[协同] WebSocket 错误:', error.message);
    removeUserFromRoom(roomId, clientId, userId);
  });

  const usersInfo = Array.from(room.users.values())
    .filter(u => u.userId !== userId)
    .map(u => ({
      userId: u.userId,
      userName: u.userName,
      joinedAt: u.joinedAt,
      cursor: u.cursor,
      selection: u.selection
    }));

  ws.send(JSON.stringify({
    event: 'roomState',
    data: {
      roomId,
      users: usersInfo,
      metadata: roomMetadata.get(roomId) || { code: '', language: 'javascript', output: [] },
      serverTime: Date.now()
    }
  }));
}

function getActiveRooms() {
  return Array.from(rooms.entries()).map(([id, room]) => ({
    id,
    userCount: room.users.size,
    createdAt: room.createdAt,
    lastActivity: room.lastActivity
  }));
}

function getRoomInfo(roomId) {
  const room = rooms.get(roomId);
  if (!room) return null;

  return {
    id: roomId,
    users: Array.from(room.users.values()).map(u => ({
      userId: u.userId,
      userName: u.userName,
      joinedAt: u.joinedAt
    })),
    userCount: room.users.size,
    createdAt: room.createdAt,
    lastActivity: room.lastActivity,
    metadata: roomMetadata.get(roomId)
  };
}

setInterval(() => {
  const now = Date.now();
  const timeout = 30 * 60 * 1000;

  for (const [roomId, room] of rooms.entries()) {
    if (now - room.lastActivity > timeout && room.users.size === 0) {
      rooms.delete(roomId);
      roomMetadata.delete(roomId);
      console.log(`[协同] 房间 ${roomId} 已销毁（超时）`);
    }
  }
}, 60000);

module.exports = {
  handleCollabConnection,
  getActiveRooms,
  getRoomInfo,
  rooms,
  roomMetadata
};
