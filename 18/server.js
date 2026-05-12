const express = require('express');
const cors = require('cors');
const http = require('http');
const { Server } = require('socket.io');
const { v4: uuidv4 } = require('uuid');
const { executeCode, cleanupAllContainers, getSupportedLanguages, LANGUAGE_CONFIG } = require('./sandbox');

const app = express();
const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  },
  pingTimeout: 10000,
  pingInterval: 5000,
  transports: ['websocket', 'polling']
});

const PORT = process.env.PORT || 3000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

const activeSessions = new Map();
const activeExecutions = new Map();
const rooms = new Map();
const roomExecutions = new Map();

function getOrCreateRoom(roomId) {
  if (rooms.has(roomId)) {
    return rooms.get(roomId);
  }

  const room = {
    id: roomId,
    users: new Map(),
    language: 'javascript',
    createdAt: Date.now(),
    lastActivity: Date.now()
  };

  rooms.set(roomId, room);
  console.log(`[房间] 房间 ${roomId} 已创建`);
  return room;
}

function removeUserFromRoom(roomId, clientId) {
  const room = rooms.get(roomId);
  if (!room) return;

  const user = room.users.get(clientId);
  if (user) {
    room.users.delete(clientId);
    room.lastActivity = Date.now();
    console.log(`[房间] 用户 ${user.userName} 离开房间 ${roomId}`);

    io.to(roomId).emit('userLeft', {
      userId: user.userId,
      userName: user.userName,
      clientId,
      leftAt: Date.now()
    });
  }

  if (room.users.size === 0) {
    setTimeout(() => {
      const currentRoom = rooms.get(roomId);
      if (currentRoom && currentRoom.users.size === 0) {
        rooms.delete(roomId);
        roomExecutions.delete(roomId);
        console.log(`[房间] 房间 ${roomId} 已销毁（无用户）`);
      }
    }, 60000);
  }
}

function broadcastToRoom(roomId, event, data, excludeSocketId = null) {
  if (excludeSocketId) {
    io.to(roomId).except(excludeSocketId).emit(event, data);
  } else {
    io.to(roomId).emit(event, data);
  }
}

io.on('connection', (socket) => {
  const sessionId = uuidv4();
  let currentRoomId = null;
  let userId = null;
  let userName = null;

  activeSessions.set(sessionId, {
    socket,
    createdAt: Date.now(),
    currentExecutionId: null
  });

  console.log(`[Socket] 客户端连接: ${socket.id} (会话: ${sessionId.slice(0, 8)})`);

  socket.on('joinRoom', ({ roomId, userId: uid, userName: uname }) => {
    if (currentRoomId) {
      socket.leave(currentRoomId);
      removeUserFromRoom(currentRoomId, socket.id);
    }

    currentRoomId = roomId;
    userId = uid || `user-${Date.now()}`;
    userName = uname || `用户${userId.slice(-4)}`;

    const room = getOrCreateRoom(roomId);
    socket.join(roomId);

    room.users.set(socket.id, {
      socket,
      userId,
      userName,
      joinedAt: Date.now()
    });
    room.lastActivity = Date.now();

    console.log(`[房间] 用户 ${userName} 加入房间 ${roomId}, 当前 ${room.users.size} 人`);

    const usersInfo = Array.from(room.users.values())
      .filter(u => u.userId !== userId)
      .map(u => ({
        userId: u.userId,
        userName: u.userName,
        joinedAt: u.joinedAt
      }));

    socket.emit('roomJoined', {
      roomId,
      language: room.language,
      users: usersInfo,
      userCount: room.users.size,
      serverTime: Date.now()
    });

    broadcastToRoom(roomId, 'userJoined', {
      userId,
      userName,
      clientId: socket.id,
      joinedAt: Date.now()
    }, socket.id);
  });

  socket.on('leaveRoom', () => {
    if (currentRoomId) {
      socket.leave(currentRoomId);
      removeUserFromRoom(currentRoomId, socket.id);
      currentRoomId = null;
    }
  });

  socket.on('changeLanguage', ({ language }) => {
    if (!currentRoomId) return;
    
    if (!LANGUAGE_CONFIG[language]) {
      socket.emit('error', { error: `不支持的语言: ${language}` });
      return;
    }

    const room = rooms.get(currentRoomId);
    if (room) {
      room.language = language;
      room.lastActivity = Date.now();

      broadcastToRoom(currentRoomId, 'languageChanged', {
        userId,
        userName,
        language,
        timestamp: Date.now()
      });

      console.log(`[房间] ${roomId} 语言切换为 ${language}`);
    }
  });

  socket.on('execute', async ({ code, language: lang }) => {
    const language = lang || (currentRoomId && rooms.get(currentRoomId)?.language) || 'javascript';

    if (!code) {
      socket.emit('error', { error: '代码不能为空' });
      return;
    }

    if (!LANGUAGE_CONFIG[language]) {
      socket.emit('error', { error: `不支持的语言: ${language}` });
      return;
    }

    const session = activeSessions.get(sessionId);
    if (!session) {
      socket.emit('error', { error: '会话不存在' });
      return;
    }

    if (session.currentExecutionId) {
      const prevExecution = activeExecutions.get(session.currentExecutionId);
      if (prevExecution && prevExecution.abortController) {
        prevExecution.abortController.abort();
      }
    }

    const executionId = uuidv4();
    const abortController = new AbortController();

    session.currentExecutionId = executionId;

    activeExecutions.set(executionId, {
      sessionId,
      roomId: currentRoomId,
      code,
      language,
      abortController,
      socket,
      createdAt: Date.now()
    });

    if (currentRoomId) {
      roomExecutions.set(currentRoomId, executionId);
      broadcastToRoom(currentRoomId, 'codeRunning', {
        userId,
        userName,
        executionId,
        language,
        timestamp: Date.now()
      }, socket.id);
    }

    console.log(`[${executionId.slice(0, 8)}] 开始执行 ${language} 代码 (会话: ${sessionId.slice(0, 8)})`);
    socket.emit('executionStart', { executionId, language });

    try {
      const result = await executeCode(code, executionId, language);

      if (abortController.signal.aborted) {
        return;
      }

      for (const outputItem of result.output) {
        socket.emit('output', outputItem);
        
        if (currentRoomId) {
          broadcastToRoom(currentRoomId, 'output', {
            userId,
            userName,
            executionId,
            ...outputItem
          }, socket.id);
        }
      }

      socket.emit('executionEnd', {
        executionId,
        exitCode: result.exitCode,
        duration: result.duration,
        language: result.language
      });

      console.log(`[${executionId.slice(0, 8)}] 执行完成 (${result.duration}ms)`);
    } catch (error) {
      if (error.message !== '执行已取消') {
        const errorOutput = {
          level: 'error',
          message: error.message,
          timestamp: new Date().toISOString()
        };
        socket.emit('output', errorOutput);

        if (currentRoomId) {
          broadcastToRoom(currentRoomId, 'output', {
            userId,
            userName,
            executionId,
            ...errorOutput
          }, socket.id);
        }

        socket.emit('executionEnd', {
          executionId,
          error: error.message,
          exitCode: 1
        });

        console.log(`[${executionId.slice(0, 8)}] 执行出错: ${error.message}`);
      }
    } finally {
      activeExecutions.delete(executionId);

      const currentSession = activeSessions.get(sessionId);
      if (currentSession) {
        currentSession.currentExecutionId = null;
      }

      if (currentRoomId && roomExecutions.get(currentRoomId) === executionId) {
        roomExecutions.delete(currentRoomId);
      }
    }
  });

  socket.on('cancel', () => {
    const session = activeSessions.get(sessionId);
    if (session && session.currentExecutionId) {
      const execution = activeExecutions.get(session.currentExecutionId);
      if (execution && execution.abortController) {
        execution.abortController.abort();
        console.log(`[${session.currentExecutionId.slice(0, 8)}] 执行已取消`);
      }
    }
  });

  socket.on('cursorUpdate', (data) => {
    if (currentRoomId) {
      broadcastToRoom(currentRoomId, 'userCursor', {
        userId,
        userName,
        ...data
      }, socket.id);
    }
  });

  socket.on('selectionUpdate', (data) => {
    if (currentRoomId) {
      broadcastToRoom(currentRoomId, 'userSelection', {
        userId,
        userName,
        ...data
      }, socket.id);
    }
  });

  socket.on('disconnect', async () => {
    console.log(`[Socket] 客户端断开: ${socket.id} (会话: ${sessionId.slice(0, 8)})`);

    if (currentRoomId) {
      removeUserFromRoom(currentRoomId, socket.id);
    }

    const session = activeSessions.get(sessionId);
    if (session && session.currentExecutionId) {
      const execution = activeExecutions.get(session.currentExecutionId);
      if (execution) {
        console.log(`[清理] 客户端断开，清理执行 ${session.currentExecutionId.slice(0, 8)}`);

        if (execution.abortController) {
          execution.abortController.abort();
        }

        if (execution.containerId) {
          try {
            const Docker = require('dockerode');
            const docker = new Docker();
            const container = docker.getContainer(execution.containerId);
            try {
              await container.stop({ t: 2 });
            } catch (e) {}
            try {
              await container.remove({ force: true, v: true });
            } catch (e) {}
          } catch (e) {
            console.error(`[清理] 删除容器失败: ${e.message}`);
          }
        }

        if (execution.tempDir) {
          const fs = require('fs');
          try {
            fs.rmSync(execution.tempDir, { recursive: true, force: true });
          } catch (e) {}
        }

        activeExecutions.delete(session.currentExecutionId);
      }
    }

    activeSessions.delete(sessionId);
    console.log(`[Socket] 会话已清理: ${sessionId.slice(0, 8)}`);
  });
});

app.get('/api/languages', (req, res) => {
  const languages = getSupportedLanguages().map(lang => ({
    value: lang,
    label: lang.charAt(0).toUpperCase() + lang.slice(1),
    version: LANGUAGE_CONFIG[lang].image
  }));

  res.json({ languages });
});

app.post('/api/execute', async (req, res) => {
  const { code, language = 'javascript' } = req.body;

  if (!code) {
    return res.status(400).json({
      error: '代码不能为空'
    });
  }

  if (!LANGUAGE_CONFIG[language]) {
    return res.status(400).json({
      error: `不支持的语言: ${language}`
    });
  }

  const executionId = uuidv4();

  try {
    console.log(`[${executionId}] 开始执行 ${language} 代码`);

    const result = await executeCode(code, executionId, language);

    console.log(`[${executionId}] 执行完成 (${result.duration}ms)`);

    res.json({
      executionId,
      output: result.output,
      error: result.error,
      duration: result.duration,
      language: result.language,
      exitCode: result.exitCode
    });
  } catch (error) {
    console.error(`[${executionId}] 执行出错:`, error.message);

    res.status(500).json({
      executionId,
      error: error.message || '执行出错',
      output: ''
    });
  }
});

app.post('/api/room/:roomId/execute', async (req, res) => {
  const { roomId } = req.params;
  const { code, language, userId, userName: uname } = req.body;

  if (!code) {
    return res.status(400).json({ error: '代码不能为空' });
  }

  const executionId = uuidv4();

  try {
    const result = await executeCode(code, executionId, language || 'javascript');

    broadcastToRoom(roomId, 'roomExecutionResult', {
      roomId,
      executionId,
      userId: userId || 'anonymous',
      userName: uname || '匿名用户',
      output: result.output,
      error: result.error,
      duration: result.duration,
      language: result.language
    });

    res.json({
      executionId,
      ...result
    });
  } catch (error) {
    res.status(500).json({
      executionId,
      error: error.message
    });
  }
});

app.get('/api/rooms', (req, res) => {
  const roomsInfo = Array.from(rooms.values()).map(room => ({
    id: room.id,
    userCount: room.users.size,
    language: room.language,
    createdAt: room.createdAt,
    lastActivity: room.lastActivity
  }));

  res.json({ rooms: roomsInfo });
});

app.get('/api/room/:roomId', (req, res) => {
  const room = rooms.get(req.params.roomId);
  if (!room) {
    return res.status(404).json({ error: '房间不存在' });
  }

  res.json({
    id: room.id,
    users: Array.from(room.users.values()).map(u => ({
      userId: u.userId,
      userName: u.userName,
      joinedAt: u.joinedAt
    })),
    userCount: room.users.size,
    language: room.language,
    createdAt: room.createdAt,
    lastActivity: room.lastActivity
  });
});

app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    activeSessions: activeSessions.size,
    activeExecutions: activeExecutions.size,
    activeRooms: rooms.size,
    languages: getSupportedLanguages(),
    timestamp: Date.now()
  });
});

server.listen(PORT, () => {
  console.log(`代码沙箱服务器运行在端口 ${PORT}`);
  console.log(`支持的语言: ${getSupportedLanguages().join(', ')}`);
  console.log(`HTTP: http://localhost:${PORT}`);
  console.log(`WebSocket: ws://localhost:${PORT}`);
  console.log(`健康检查: http://localhost:${PORT}/health`);
});

const gracefulShutdown = async (signal) => {
  console.log(`\n收到 ${signal} 信号，优雅关闭...`);

  console.log(`[清理] 断开 ${activeSessions.size} 个活跃会话`);
  for (const [sessionId, session] of activeSessions.entries()) {
    try {
      session.socket.disconnect(true);
    } catch (e) {}
  }

  console.log(`[清理] 清理 ${activeExecutions.size} 个活跃执行`);
  for (const [executionId, execution] of activeExecutions.entries()) {
    try {
      if (execution.abortController) {
        execution.abortController.abort();
      }

      if (execution.timeoutTimer) {
        clearTimeout(execution.timeoutTimer);
      }

      if (execution.containerId) {
        try {
          const Docker = require('dockerode');
          const docker = new Docker();
          const container = docker.getContainer(execution.containerId);
          try {
            await container.stop({ t: 2 });
          } catch (e) {}
          try {
            await container.remove({ force: true, v: true });
          } catch (e) {}
        } catch (e) {}
      }

      if (execution.tempDir) {
        const fs = require('fs');
        try {
          fs.rmSync(execution.tempDir, { recursive: true, force: true });
        } catch (e) {}
      }
    } catch (e) {
      console.error(`[清理] 执行 ${executionId.slice(0, 8)} 清理失败:`, e.message);
    }
  }

  activeExecutions.clear();
  activeSessions.clear();
  rooms.clear();
  roomExecutions.clear();

  await cleanupAllContainers();

  server.close(() => {
    console.log('服务器已关闭');
    process.exit(0);
  });

  setTimeout(() => {
    console.error('强制退出');
    process.exit(1);
  }, 10000);
};

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

process.on('uncaughtException', (error) => {
  console.error('服务器未捕获异常:', error);
});

process.on('unhandledRejection', (reason) => {
  console.error('服务器未处理的 Promise 拒绝:', reason);
});

setInterval(() => {
  const now = Date.now();
  const timeout = 30 * 60 * 1000;

  for (const [roomId, room] of rooms.entries()) {
    if (now - room.lastActivity > timeout && room.users.size === 0) {
      rooms.delete(roomId);
      roomExecutions.delete(roomId);
      console.log(`[房间] 房间 ${roomId} 已销毁（超时）`);
    }
  }
}, 60000);
