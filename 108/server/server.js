const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const Y = require('yjs');
const { Level } = require('level');
const { setupWSConnection } = require('y-websocket/bin/utils');
const WebSocket = require('ws');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);

const io = new Server(server, {
  cors: {
    origin: "http://localhost:3000",
    methods: ["GET", "POST"]
  },
  pingTimeout: 60000,
  pingInterval: 25000
});

const db = new Level('./yjs-db', { valueEncoding: 'json' });

const ydocSessions = new Map();
const users = new Map();
const docUsers = new Map();
const docComments = new Map();

function getYDoc(docId) {
  if (!ydocSessions.has(docId)) {
    const ydoc = new Y.Doc({ guid: docId });
    
    ydocSessions.set(docId, ydoc);
    
    (async () => {
      try {
        const savedState = await db.get(`doc:${docId}`).catch(() => null);
        if (savedState) {
          Y.applyUpdate(ydoc, Buffer.from(savedState, 'base64'));
          console.log(`Loaded document ${docId} from database`);
        }
      } catch (e) {
        console.log(`No existing data for ${docId}, starting fresh`);
      }
    })();
    
    ydoc.on('update', (update, origin) => {
      if (origin !== 'server') {
        (async () => {
          try {
            const currentState = Y.encodeStateAsUpdate(ydoc);
            await db.put(`doc:${docId}`, Buffer.from(currentState).toString('base64'));
          } catch (e) {
            console.error('Error saving document:', e);
          }
        })();
      }
    });
  }
  return ydocSessions.get(docId);
}

const wss = new WebSocket.Server({ 
  server: server, 
  path: '/yjs'
});

wss.on('connection', (conn, req) => {
  console.log('Yjs WebSocket connection established');
  
  setupWSConnection(conn, req, {
    gc: true,
    docName: req.url.slice(1).split('?')[0].replace('yjs/', '')
  });
  
  conn.on('close', () => {
    console.log('Yjs WebSocket connection closed');
  });
  
  conn.on('error', (error) => {
    console.error('Yjs WebSocket error:', error);
  });
});

function getDocUsers(docId) {
  return docUsers.get(docId) || [];
}

function addDocUser(docId, user) {
  const users = docUsers.get(docId) || [];
  const existingIndex = users.findIndex(u => u.id === user.id);
  if (existingIndex === -1) {
    users.push(user);
    docUsers.set(docId, users);
  } else {
    users[existingIndex] = user;
  }
  return users;
}

function removeDocUser(docId, userId) {
  const users = docUsers.get(docId) || [];
  const filteredUsers = users.filter(u => u.id !== userId);
  docUsers.set(docId, filteredUsers);
  return filteredUsers;
}

function addComment(docId, comment) {
  const comments = docComments.get(docId) || [];
  const newComment = {
    id: uuidv4(),
    ...comment,
    timestamp: new Date().toISOString(),
    resolved: false,
    replies: []
  };
  comments.push(newComment);
  docComments.set(docId, comments);
  return newComment;
}

function getComments(docId) {
  return docComments.get(docId) || [];
}

function resolveComment(docId, commentId) {
  const comments = docComments.get(docId) || [];
  const comment = comments.find(c => c.id === commentId);
  if (comment) {
    comment.resolved = true;
  }
  return comment;
}

function addReply(docId, commentId, reply) {
  const comments = docComments.get(docId) || [];
  const comment = comments.find(c => c.id === commentId);
  if (comment) {
    const newReply = {
      id: uuidv4(),
      ...reply,
      timestamp: new Date().toISOString()
    };
    comment.replies.push(newReply);
    return newReply;
  }
  return null;
}

io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  socket.on('join-document', async ({ docId, userId, userName }) => {
    try {
      socket.join(docId);
      
      const user = {
        id: userId,
        name: userName,
        socketId: socket.id,
        cursor: null,
        selection: null,
        color: getRandomColor(),
        isOnline: true,
        lastActive: new Date().toISOString()
      };
      
      users.set(socket.id, { ...user, docId });
      const usersInDoc = addDocUser(docId, user);

      getYDoc(docId);
      const comments = getComments(docId);
      
      socket.emit('document-ready', { docId, comments });
      
      io.to(docId).emit('user-joined', { user, users: usersInDoc });
      io.to(docId).emit('active-users', usersInDoc);
      
      console.log(`${userName} joined document ${docId}`);
    } catch (error) {
      console.error('Error joining document:', error);
      socket.emit('error', { message: 'Failed to join document' });
    }
  });

  socket.on('reconnect-document', async ({ docId, userId, userName }) => {
    try {
      socket.join(docId);
      
      const existingUser = [...users.values()].find(u => u.id === userId);
      const user = existingUser || {
        id: userId,
        name: userName,
        socketId: socket.id,
        cursor: null,
        selection: null,
        color: getRandomColor(),
        isOnline: true,
        lastActive: new Date().toISOString()
      };
      user.socketId = socket.id;
      user.isOnline = true;
      user.docId = docId;
      
      users.set(socket.id, user);
      addDocUser(docId, user);

      const comments = getComments(docId);
      socket.emit('document-ready', { docId, comments });
      
      const usersInDoc = getDocUsers(docId);
      io.to(docId).emit('active-users', usersInDoc);
      
      addNotification(docId, `${userName} 重新连接了`, 'join');
      console.log(`${userName} reconnected to document ${docId}`);
    } catch (error) {
      console.error('Error reconnecting:', error);
    }
  });

  socket.on('cursor-update', ({ docId, userId, cursor, selection }) => {
    const user = users.get(socket.id);
    if (user) {
      user.cursor = cursor;
      user.selection = selection;
      user.lastActive = new Date().toISOString();
      
      socket.to(docId).emit('cursor-moved', { 
        userId, 
        cursor, 
        selection,
        userName: user.name, 
        color: user.color 
      });
    }
  });

  socket.on('user-presence', ({ docId, userId, status }) => {
    const user = users.get(socket.id);
    if (user) {
      user.isOnline = status === 'online';
      user.lastActive = new Date().toISOString();
      
      const usersInDoc = getDocUsers(docId);
      io.to(docId).emit('active-users', usersInDoc);
    }
  });

  socket.on('add-comment', ({ docId, comment }) => {
    const user = users.get(socket.id);
    const newComment = addComment(docId, {
      ...comment,
      userId: user.id,
      userName: user.name,
      userColor: user.color
    });
    
    io.to(docId).emit('comment-added', newComment);
    addNotification(docId, `${user.name} 添加了新评论`, 'comment');
    
    const mentionedUsers = comment.text.match(/@(\w+)/g);
    if (mentionedUsers) {
      mentionedUsers.forEach(mention => {
        const mentionedName = mention.substring(1);
        const usersInDoc = getDocUsers(docId);
        const mentionedUser = usersInDoc.find(u => u.name === mentionedName);
        if (mentionedUser) {
          io.to(mentionedUser.socketId).emit('mention-notification', {
            from: user.name,
            text: comment.text,
            docId,
            timestamp: new Date().toISOString()
          });
        }
      });
    }
  });

  socket.on('resolve-comment', ({ docId, commentId }) => {
    const user = users.get(socket.id);
    const comment = resolveComment(docId, commentId);
    if (comment) {
      io.to(docId).emit('comment-resolved', { commentId, resolvedBy: user.name });
      addNotification(docId, `${user.name} 解决了一条评论`, 'comment');
    }
  });

  socket.on('add-reply', ({ docId, commentId, reply }) => {
    const user = users.get(socket.id);
    const newReply = addReply(docId, commentId, {
      ...reply,
      userId: user.id,
      userName: user.name,
      userColor: user.color
    });
    
    if (newReply) {
      io.to(docId).emit('reply-added', { commentId, reply: newReply });
      
      const mentionedUsers = reply.text.match(/@(\w+)/g);
      if (mentionedUsers) {
        mentionedUsers.forEach(mention => {
          const mentionedName = mention.substring(1);
          const usersInDoc = getDocUsers(docId);
          const mentionedUser = usersInDoc.find(u => u.name === mentionedName);
          if (mentionedUser) {
            io.to(mentionedUser.socketId).emit('mention-notification', {
              from: user.name,
              text: reply.text,
              docId,
              timestamp: new Date().toISOString()
            });
          }
        });
      }
    }
  });

  socket.on('save-version', async ({ docId, userId, snapshot }) => {
    try {
      const versions = await db.get(`versions:${docId}`).catch(() => []);
      const newVersion = {
        id: uuidv4(),
        version: versions.length + 1,
        timestamp: new Date().toISOString(),
        snapshot: snapshot,
        savedBy: userId
      };
      versions.push(newVersion);
      await db.put(`versions:${docId}`, versions);
      
      io.to(docId).emit('version-saved', newVersion);
      addNotification(docId, `版本 ${newVersion.version} 已保存`, 'join');
    } catch (error) {
      console.error('Error saving version:', error);
      socket.emit('error', { message: 'Failed to save version' });
    }
  });

  socket.on('get-versions', async ({ docId }) => {
    try {
      const versions = await db.get(`versions:${docId}`).catch(() => []);
      socket.emit('versions-list', versions);
    } catch (error) {
      console.error('Error getting versions:', error);
      socket.emit('versions-list', []);
    }
  });

  socket.on('disconnect', () => {
    const user = users.get(socket.id);
    if (user) {
      const docId = user.docId;
      if (docId) {
        user.isOnline = false;
        user.lastActive = new Date().toISOString();
        
        const remainingUsers = removeDocUser(docId, user.id);
        
        io.to(docId).emit('user-left', { user });
        io.to(docId).emit('cursor-cleanup', { userId: user.id });
        io.to(docId).emit('active-users', remainingUsers);
        
        addNotification(docId, `${user.name} 离开了文档`, 'leave');
      }
      users.delete(socket.id);
      console.log('User disconnected:', user.name);
    }
  });
});

function addNotification(docId, message, type) {
  io.to(docId).emit('notification', { message, type, id: Date.now() });
}

function getRandomColor() {
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
    '#FF8C42', '#6C5CE7', '#00B894', '#E17055'
  ];
  return colors[Math.floor(Math.random() * colors.length)];
}

app.get('/api/docs/:docId/exists', async (req, res) => {
  const { docId } = req.params;
  try {
    await db.get(`doc:${docId}`);
    res.json({ exists: true });
  } catch {
    res.json({ exists: false });
  }
});

app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    yjsSessions: ydocSessions.size,
    connectedUsers: users.size
  });
});

const PORT = process.env.PORT || 3001;
server.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📡 Yjs WebSocket: ws://localhost:${PORT}/yjs`);
  console.log(`💾 Database persisted in ./yjs-db`);
});
