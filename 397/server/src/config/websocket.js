const { Server } = require('socket.io');
const http = require('http');

let io = null;

const initWebSocket = (server) => {
  io = new Server(server, {
    cors: {
      origin: '*',
      methods: ['GET', 'POST']
    }
  });

  io.on('connection', (socket) => {
    console.log('客户端连接:', socket.id);

    socket.on('joinTemplate', (templateId) => {
      socket.join(`template:${templateId}`);
      console.log(`客户端 ${socket.id} 加入模板房间: ${templateId}`);
    });

    socket.on('leaveTemplate', (templateId) => {
      socket.leave(`template:${templateId}`);
      console.log(`客户端 ${socket.id} 离开模板房间: ${templateId}`);
    });

    socket.on('disconnect', () => {
      console.log('客户端断开连接:', socket.id);
    });
  });

  return io;
};

const getIO = () => {
  if (!io) {
    throw new Error('WebSocket 未初始化');
  }
  return io;
};

const broadcastTemplateStats = (templateId, stats) => {
  if (io) {
    io.to(`template:${templateId}`).emit('templateStatsUpdate', stats);
    console.log(`广播模板 ${templateId} 统计更新:`, stats);
  }
};

const broadcastGlobalStats = (stats) => {
  if (io) {
    io.emit('globalStatsUpdate', stats);
    console.log('广播全局统计更新:', stats);
  }
};

module.exports = {
  initWebSocket,
  getIO,
  broadcastTemplateStats,
  broadcastGlobalStats
};
