import express from 'express';
import http from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import fs from 'fs';
import { v4 as uuidv4 } from 'uuid';
import RecordingManager from './RecordingManager.js';
import MeetingMinutesManager from './MeetingMinutesManager.js';

const app = express();
const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  },
  maxHttpBufferSize: 1e8
});

app.use(cors());
app.use(express.json());

const MAX_PARTICIPANTS = 50;

const rooms = new Map();
const recordingManager = new RecordingManager();
const minutesManager = new MeetingMinutesManager();

const getRoom = (roomId) => {
  if (!rooms.has(roomId)) {
    rooms.set(roomId, {
      id: roomId,
      participants: new Map(),
      messages: [],
      createdAt: Date.now(),
      isRecording: false,
      recordingInfo: null
    });
  }
  return rooms.get(roomId);
};

const removeFromRoom = (socket, roomId) => {
  const room = rooms.get(roomId);
  if (!room) return;

  const participant = room.participants.get(socket.id);
  if (participant) {
    room.participants.delete(socket.id);
    socket.leave(roomId);

    if (room.isRecording) {
      recordingManager.removeParticipantStream(roomId, socket.id);
    }

    io.to(roomId).emit('participant-left', {
      id: socket.id,
      user: participant.user
    });

    if (room.participants.size === 0) {
      if (room.isRecording) {
        recordingManager.stopRecording(roomId);
        room.isRecording = false;
        room.recordingInfo = null;
      }
      rooms.delete(roomId);
    }
  }
};

const getParticipantsList = (room) => {
  return Array.from(room.participants.entries()).map(([id, data]) => ({
    id,
    user: data.user,
    isMuted: data.isMuted,
    isVideoOn: data.isVideoOn,
    isScreenSharing: data.isScreenSharing,
    joinedAt: data.joinedAt
  }));
};

io.on('connection', (socket) => {
  console.log('Client connected:', socket.id);

  socket.on('create-room', ({ user }, callback) => {
    const roomId = uuidv4().slice(0, 8).toUpperCase();
    const room = getRoom(roomId);

    if (room.participants.size >= MAX_PARTICIPANTS) {
      return callback?.({ success: false, error: 'Room is full' });
    }

    socket.join(roomId);
    room.participants.set(socket.id, {
      user,
      isMuted: false,
      isVideoOn: true,
      isScreenSharing: false,
      joinedAt: Date.now()
    });

    callback?.({
      success: true,
      roomId,
      participants: getParticipantsList(room),
      isRecording: room.isRecording,
      recordingInfo: room.recordingInfo
    });
  });

  socket.on('join-room', ({ roomId, user }, callback) => {
    const room = getRoom(roomId);

    if (room.participants.size >= MAX_PARTICIPANTS) {
      return callback?.({
        success: false,
        error: `会议已满（最多${MAX_PARTICIPANTS}人）`
      });
    }

    const existingParticipant = Array.from(room.participants.values())
      .find(p => p.user.id === user.id);

    if (existingParticipant) {
      return callback?.({
        success: false,
        error: '该用户已在会议中'
      });
    }

    socket.join(roomId);
    room.participants.set(socket.id, {
      user,
      isMuted: false,
      isVideoOn: true,
      isScreenSharing: false,
      joinedAt: Date.now()
    });

    if (room.isRecording) {
      recordingManager.addParticipantStream(roomId, socket.id, {
        user,
        joinedAt: Date.now()
      });
    }

    minutesManager.addParticipant(roomId, {
      id: socket.id,
      user,
      joinedAt: Date.now()
    });

    const participants = getParticipantsList(room);
    const others = participants.filter(p => p.id !== socket.id);

    callback?.({
      success: true,
      roomId,
      participants,
      messages: room.messages.slice(-100),
      isRecording: room.isRecording,
      recordingInfo: room.recordingInfo
    });

    socket.to(roomId).emit('participant-joined', {
      id: socket.id,
      user,
      participants
    });

    if (room.isRecording) {
      socket.emit('recording-started', room.recordingInfo);
    }
  });

  socket.on('offer', ({ to, offer }) => {
    socket.to(to).emit('offer', {
      from: socket.id,
      offer
    });
  });

  socket.on('answer', ({ to, answer }) => {
    socket.to(to).emit('answer', {
      from: socket.id,
      answer
    });
  });

  socket.on('ice-candidate', ({ to, candidate }) => {
    socket.to(to).emit('ice-candidate', {
      from: socket.id,
      candidate
    });
  });

  socket.on('update-media-state', ({ roomId, isMuted, isVideoOn, isScreenSharing }) => {
    const room = rooms.get(roomId);
    if (!room) return;

    const participant = room.participants.get(socket.id);
    if (participant) {
      if (typeof isMuted === 'boolean') participant.isMuted = isMuted;
      if (typeof isVideoOn === 'boolean') participant.isVideoOn = isVideoOn;
      if (typeof isScreenSharing === 'boolean') participant.isScreenSharing = isScreenSharing;

      io.to(roomId).emit('media-state-updated', {
        id: socket.id,
        isMuted: participant.isMuted,
        isVideoOn: participant.isVideoOn,
        isScreenSharing: participant.isScreenSharing
      });
    }
  });

  socket.on('send-message', ({ roomId, content, type = 'text' }) => {
    const room = rooms.get(roomId);
    if (!room) return;

    const participant = room.participants.get(socket.id);
    if (!participant) return;

    const message = {
      id: uuidv4(),
      userId: participant.user.id,
      userName: participant.user.name,
      userAvatar: participant.user.avatar,
      content,
      type,
      timestamp: Date.now()
    };

    room.messages.push(message);
    if (room.messages.length > 500) {
      room.messages = room.messages.slice(-500);
    }

    minutesManager.addMessage(roomId, message);

    io.to(roomId).emit('message-received', message);
  });

  socket.on('raise-hand', ({ roomId, raised }) => {
    const room = rooms.get(roomId);
    if (!room) return;

    const participant = room.participants.get(socket.id);
    if (!participant) return;

    io.to(roomId).emit('hand-raised', {
      id: socket.id,
      raised,
      user: participant.user
    });
  });

  socket.on('start-recording', async ({ roomId, layout = 'grid' }, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      return callback?.({ success: false, error: 'Room not found' });
    }

    if (room.isRecording) {
      return callback?.({ success: false, error: 'Recording already in progress' });
    }

    const result = await recordingManager.startRecording(roomId, layout);
    
    if (result.success) {
      room.isRecording = true;
      room.recordingInfo = {
        recordingId: result.recordingId,
        wsPort: result.wsPort,
        startedAt: Date.now(),
        layout
      };

      room.participants.forEach((participant, participantId) => {
        recordingManager.addParticipantStream(roomId, participantId, {
          user: participant.user,
          joinedAt: participant.joinedAt
        });
      });

      io.to(roomId).emit('recording-started', room.recordingInfo);
    }

    callback?.(result);
  });

  socket.on('stop-recording', async ({ roomId }, callback) => {
    const room = rooms.get(roomId);
    if (!room) {
      return callback?.({ success: false, error: 'Room not found' });
    }

    if (!room.isRecording) {
      return callback?.({ success: false, error: 'No recording in progress' });
    }

    const result = await recordingManager.stopRecording(roomId);
    
    if (result.success) {
      room.isRecording = false;
      room.recordingInfo = null;

      io.to(roomId).emit('recording-stopped', {
        recordingId: result.recordingId,
        filename: result.filename,
        duration: result.duration,
        fileSize: result.fileSize,
        url: `/api/recordings/${result.filename}`
      });
    }

    callback?.(result);
  });

  socket.on('get-recording-stats', ({ roomId }, callback) => {
    const stats = recordingManager.getRecordingStats(roomId);
    callback?.({ success: !!stats, stats });
  });

  socket.on('generate-minutes', async ({ roomId }, callback) => {
    try {
      const result = await minutesManager.generateMinutes(roomId);
      callback?.(result);
      
      if (result.success) {
        io.to(roomId).emit('minutes-updated', {
          roomId,
          summary: result.summary
        });
      }
    } catch (error) {
      callback?.({ success: false, error: error.message });
    }
  });

  socket.on('get-minutes-stats', ({ roomId }, callback) => {
    const stats = minutesManager.getSessionStats(roomId);
    callback?.({ success: !!stats, stats });
  });

  socket.on('end-meeting', async ({ roomId }, callback) => {
    try {
      const minutesResult = await minutesManager.generateMinutes(roomId);
      const sessionData = minutesManager.endSession(roomId);
      
      if (room.isRecording) {
        await recordingManager.stopRecording(roomId);
        room.isRecording = false;
        room.recordingInfo = null;
      }

      io.to(roomId).emit('meeting-ended', {
        roomId,
        minutes: minutesResult.success ? minutesResult.summary : null,
        sessionData
      });

      callback?.({ 
        success: true, 
        minutes: minutesResult.success ? minutesResult.summary : null,
        error: minutesResult.error 
      });
    } catch (error) {
      callback?.({ success: false, error: error.message });
    }
  });

  socket.on('leave-room', ({ roomId }) => {
    removeFromRoom(socket, roomId);
  });

  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id);
    
    for (const [roomId, room] of rooms.entries()) {
      if (room.participants.has(socket.id)) {
        removeFromRoom(socket, roomId);
        break;
      }
    }
  });
});

app.get('/api/rooms/:roomId/exists', (req, res) => {
  const { roomId } = req.params;
  const room = rooms.get(roomId);
  res.json({ exists: !!room, participantCount: room?.participants.size || 0 });
});

app.get('/api/rooms/:roomId/participants', (req, res) => {
  const { roomId } = req.params;
  const room = rooms.get(roomId);
  
  if (!room) {
    return res.status(404).json({ error: 'Room not found' });
  }

  res.json({
    participants: getParticipantsList(room)
  });
});

app.get('/api/recordings', (req, res) => {
  const recordings = recordingManager.listRecordings();
  res.json({ recordings });
});

app.get('/api/recordings/:filename', (req, res) => {
  const { filename } = req.params;
  const filePath = recordingManager.getRecordingFilePath(filename);
  
  if (!filePath) {
    return res.status(404).json({ error: 'Recording not found' });
  }

  res.download(filePath, filename, (err) => {
    if (err) {
      console.error('Error downloading recording:', err);
      res.status(500).json({ error: 'Failed to download recording' });
    }
  });
});

app.delete('/api/recordings/:filename', (req, res) => {
  const { filename } = req.params;
  const success = recordingManager.deleteRecording(filename);
  
  if (success) {
    res.json({ success: true });
  } else {
    res.status(404).json({ error: 'Recording not found' });
  }
});

app.get('/api/recordings/active', (req, res) => {
  const sessions = recordingManager.getAllSessions();
  res.json({ sessions });
});

app.get('/api/minutes', (req, res) => {
  const minutes = minutesManager.listMinutes();
  res.json({ minutes });
});

app.get('/api/minutes/:filename', (req, res) => {
  const { filename } = req.params;
  const minutes = minutesManager.getMinutes(filename);
  
  if (!minutes) {
    return res.status(404).json({ error: 'Meeting minutes not found' });
  }

  res.json(minutes);
});

app.get('/api/minutes/:filename/download', (req, res) => {
  const { filename } = req.params;
  const filePath = minutesManager.getMinutesFilePath(filename);
  
  if (!filePath) {
    return res.status(404).json({ error: 'Meeting minutes not found' });
  }

  const jsonContent = fs.readFileSync(filePath, 'utf8');
  const data = JSON.parse(jsonContent);
  
  let markdown = `# ${data.summary?.title || '会议纪要'}\n\n`;
  markdown += `**时间**: ${new Date(data.startTime).toLocaleString('zh-CN')}\n`;
  markdown += `**时长**: ${Math.round((data.endTime - data.startTime) / 60000)} 分钟\n`;
  markdown += `**参会人员**: ${data.participants?.map(p => p.name).join('、')}\n\n`;

  if (data.summary?.overallSummary) {
    markdown += `## 会议概述\n\n${data.summary.overallSummary}\n\n`;
  }

  if (data.summary?.keyPoints?.length > 0) {
    markdown += `## 核心讨论要点\n\n`;
    data.summary.keyPoints.forEach((point, i) => {
      markdown += `${i + 1}. ${point}\n`;
    });
    markdown += `\n`;
  }

  if (data.summary?.decisions?.length > 0) {
    markdown += `## 会议决议\n\n`;
    data.summary.decisions.forEach((decision, i) => {
      markdown += `${i + 1}. ${decision}\n`;
    });
    markdown += `\n`;
  }

  if (data.summary?.actionItems?.length > 0) {
    markdown += `## 待办事项\n\n`;
    markdown += `| 序号 | 内容 | 负责人 | 优先级 |\n`;
    markdown += `| --- | --- | --- | --- |\n`;
    data.summary.actionItems.forEach((item, i) => {
      const priorityText = { high: '高', medium: '中', low: '低' }[item.priority] || '中';
      markdown += `| ${i + 1} | ${item.content} | ${item.assignee} | ${priorityText} |\n`;
    });
    markdown += `\n`;
  }

  if (data.summary?.nextMeeting) {
    markdown += `## 下次会议建议\n\n${data.summary.nextMeeting}\n\n`;
  }

  if (data.summary?.autoGenerated) {
    markdown += `> 本纪要由AI自动生成，仅供参考\n`;
  }

  res.setHeader('Content-Type', 'text/markdown; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="${filename.replace('.json', '.md')}"`);
  res.send(markdown);
});

app.delete('/api/minutes/:filename', (req, res) => {
  const { filename } = req.params;
  const success = minutesManager.deleteMinutes(filename);
  
  if (success) {
    res.json({ success: true });
  } else {
    res.status(404).json({ error: 'Meeting minutes not found' });
  }
});

app.get('/api/minutes/active', (req, res) => {
  const sessions = minutesManager.getAllSessions();
  res.json({ sessions });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    activeRooms: rooms.size,
    activeRecordings: recordingManager.getAllSessions().length,
    activeMinutes: minutesManager.getAllSessions().length,
    uptime: process.uptime()
  });
});

const PORT = process.env.PORT || 3001;

server.listen(PORT, () => {
  console.log(`Signaling server running on port ${PORT}`);
  console.log(`Max participants per room: ${MAX_PARTICIPANTS}`);
  console.log(`Recording directory: server/recordings`);
  console.log(`API Endpoints:`);
  console.log(`  GET  /api/health - Health check`);
  console.log(`  GET  /api/rooms/:roomId/exists - Check room exists`);
  console.log(`  GET  /api/rooms/:roomId/participants - List participants`);
  console.log(`  GET  /api/recordings - List all recordings`);
  console.log(`  GET  /api/recordings/:filename - Download recording`);
  console.log(`  DELETE /api/recordings/:filename - Delete recording`);
  console.log(`  GET  /api/recordings/active - List active recordings`);
});
